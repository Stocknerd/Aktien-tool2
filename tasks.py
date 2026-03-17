import time
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import saas_logic
import core
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

executor = ThreadPoolExecutor(max_workers=4)

def process_task(task_id):
    task = saas_logic.get_task(task_id)
    if not task:
        return

    saas_logic.update_task(task_id, "processing")
    logging.info(f"Processing task {task_id} ({task['type']})")

    try:
        payload = json.loads(task['payload'])
        
        if task['type'] == 'render':
            ticker = payload.get('ticker')
            selected = payload.get('metrics', [])
            layout_mode = payload.get('layout', 'default')
            watermark = payload.get('watermark', '')
            
            df = core.load_df()
            row = df[df['Symbol'] == ticker]
            if row.empty:
                raise Exception(f"Ticker {ticker} not found")
            
            img = core.render_stock_card(row.iloc[0], selected, layout_mode, watermark)
            
            ts = time.strftime("%Y%m%d_%H%M%S")
            filename = f"ASYNC_{ticker}_{ts}.png"
            path = os.path.join(core.OUT_DIR, filename)
            img.convert('RGB').save(path, format='PNG')
            
            saas_logic.update_task(task_id, "completed", result_url=f"/output/{filename}")
            saas_logic.log_usage(task['token'], "render_async")

        elif task['type'] == 'compare':
            ticker_a = payload.get('ticker_a')
            ticker_b = payload.get('ticker_b')
            metrics = payload.get('metrics', core.DEFAULT_METRICS)
            watermark = payload.get('watermark', '')
            
            df = core.load_df()
            rows_a = df[df['Symbol'] == ticker_a]
            rows_b = df[df['Symbol'] == ticker_b]
            
            if rows_a.empty or rows_b.empty:
                raise Exception("One or both tickers not found")
                
            img = core.render_compare([rows_a.iloc[0], rows_b.iloc[0]], metrics, watermark=watermark, fetch_analyst=True)
            
            ts = time.strftime("%Y%m%d_%H%M%S")
            filename = f"ASYNC_COMPARE_{ticker_a}_{ticker_b}_{ts}.png"
            path = os.path.join(core.OUT_DIR, filename)
            img.convert('RGB').save(path, format="PNG")
            
            saas_logic.update_task(task_id, "completed", result_url=f"/static/generated/{filename}")
            saas_logic.log_usage(task['token'], "compare_async")

    except Exception as e:
        logging.error(f"Task {task_id} failed: {str(e)}")
        saas_logic.update_task(task_id, "failed", error=str(e))

def enqueue_task(token, task_type, payload):
    task_id = saas_logic.add_task(token, task_type, payload)
    executor.submit(process_task, task_id)
    return task_id
