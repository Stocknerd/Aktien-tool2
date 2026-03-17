import os
import time
import json
import logging
import uuid
import shutil
from datetime import datetime
from flask import request, jsonify, g, make_response

# ───────────────────────── JSON Formatter ─────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "route"):
            log_record["route"] = record.route
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms
        if hasattr(record, "status"):
            log_record["status"] = record.status
        if hasattr(record, "tickers"):
            log_record["tickers"] = record.tickers

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_ops(app, csv_path):
    # D16: Sentry
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            sentry_sdk.init(dsn=sentry_dsn, integrations=[FlaskIntegration()])
            app.logger.info("Sentry initialized")
        except ImportError:
            app.logger.warning("SENTRY_DSN set but sentry_sdk not installed.")

    # D14: Structured Logging (JSON only if not in Debug/local)
    if not app.debug:
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(JSONFormatter())
        app.logger.handlers = [log_handler]
        app.logger.setLevel(logging.INFO)
        # quiet werkzeug in production
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
    else:
        # In Debug mode, keep standard logs so the user sees the "Running on..." link
        app.logger.setLevel(logging.INFO)
        logging.getLogger('werkzeug').setLevel(logging.INFO)

    # In-memory Rate Limit
    rate_limits = {}

    @app.before_request
    def before_request():
        g.start_time = time.time()
        g.request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        
        # Rate Limit (einfach: 60 req / min per IP)
        ip = request.remote_addr
        now = time.time()
        if ip not in rate_limits:
            rate_limits[ip] = []
        rate_limits[ip] = [t for t in rate_limits[ip] if now - t < 60]
        if len(rate_limits[ip]) > 60:
            return "Too Many Requests", 429
        rate_limits[ip].append(now)

    @app.after_request
    def after_request(response):
        duration_ms = int((time.time() - g.start_time) * 1000)
        
        # D17: Security Headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Allow framing from the main blog if embed mode is active
        if request.args.get('embed') == '1' or getattr(g, 'is_landing_page', False) or request.form.get('is_embedded') == '1':
            response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://schatzsuche40.de https://*.schatzsuche40.de;"
            # We'll let Nginx handle the removal of X-Frame-Options for better reliability
        else:
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Extract tickers from common args
        t = request.args.get('ticker') or request.form.get('ticker') or ''
        ta = request.args.get('ticker_a') or request.args.get('t1') or ''
        tb = request.args.get('ticker_b') or request.args.get('t2') or ''
        tickers = [x.upper() for x in [t, ta, tb] if x.strip()]

        extra = {
            "request_id": g.request_id,
            "route": request.path,
            "duration_ms": duration_ms,
            "status": response.status_code,
            "tickers": ",".join(tickers) if tickers else None
        }
        
        app.logger.info("HTTP Request", extra=extra)
        return response

    # D15: Healthchecks
    @app.route('/health')
    def health():
        return jsonify({"status": "ok", "app": app.name})

    @app.route('/health/data')
    def health_data():
        if not os.path.exists(csv_path):
            return jsonify({"status": "error", "message": "CSV missing"}), 404
        
        mtime = os.path.getmtime(csv_path)
        days_old = (time.time() - mtime) / 86400.0
        return jsonify({
            "status": "ok" if days_old < 2 else "stale",
            "days_old": round(days_old, 2),
            "last_update": datetime.fromtimestamp(mtime).isoformat()
        }), 200 if days_old < 2 else 207

    @app.route('/health/disk')
    def health_disk():
        # Use current drive root for disk usage (OS agnostic)
        total, used, free = shutil.disk_usage(os.path.abspath(os.sep))
        free_gb = free // (2**30)
        return jsonify({
            "status": "ok" if free_gb > 1 else "warning",
            "free_space_gb": free_gb
        }), 200 if free_gb > 1 else 207
