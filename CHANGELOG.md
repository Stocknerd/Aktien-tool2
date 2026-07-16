# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-07-16
### Added
- Schema-2 Canva queue with reviewed-export approval, media checksum and explicit platform contracts.
- Fail-closed native browser publisher for YouTube-private and Facebook-draft actions, including target verification, persisted-result checks, packet locking and duplicate fingerprints.
- Optional `requirements-browser.txt` and executable workflow documentation.

### Changed
- Public social API dispatch now requires both `PREPARE_MANUAL_UPLOAD=False` and `PUBLIC_PUBLISHING_ALLOWED=True`.
- Google Drive transfers separately require both `UPLOAD_TO_GDRIVE=True` and `GDRIVE_TRANSFER_ALLOWED=True`.
- Current-news drafts accept only fresh, dated HTTPS source records, preserve provenance and always remain review-only.
- Generated content is schema-, length-, disclaimer- and voiceover-validated before image or video rendering.
- The quality-first Europe/Berlin cron mix is rendered directly from the performance schedule and installed fail-closed with a backup.
- AI output preparation is centrally short-circuited before every external dispatcher.
- Dividend calendars skip publication instead of filling missing source data with synthetic dates, currencies, yields or payouts.

## [1.1.0] - 2026-03-05
### Added
- **Core (Phase 1A)**: Retry and backoff logic for CSV pipelines. Improved ticker normalization (`.B` to `-B`), global data freshness metrics in the UI, and data quality checks script exporting to `logs/`.
- **Image Generator (Phase 1B)**: Added `layout=dark` feature for generating images in dark mode layout. Dynamic placeholders for missing logos with text initials. Better cleanup script spanning multiple output directories.
- **Compare App (Phase 1C)**: Polish for the `/compare` endpoint with shareable permalinks and one-click comparison presets in the UI. Graceful degradation when metrics are missing.
- **Ops & Observability (Phase 1D)**: New `ops_middleware.py` adding structured JSON logging, simple IP-based rate limiting, Sentry integration (`SENTRY_DSN`), and standardized health checks (`/health`, `/health/data`, `/health/disk`).
- **Release (Phase 1E)**: Initial GitHub Actions CI pipeline and Dependabot configuration. Optional Monetization prep structure included (Docs, config flags).

### Changed
- Refactored rendering core in `compare_app.py` and `app.py` to prevent text overflows via `shrink_to_fit` methods.
- CSV pipelines now natively support resilient parallel data fetching.
