# SearchSift

<img width="1380" height="820" alt="Screenshot 2026-02-05 at 11 19 58 AM" src="https://github.com/user-attachments/assets/60f607ef-2852-400d-a0f3-80cf37f5e2e5" />


A local-first browser extension + backend that captures your search queries and search-result clicks, automatically categorizes them, and produces daily reports.

## Quick Start

```bash
# 1. Create and activate virtual environment
cd SearchSift
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate API key and configure
python scripts/generate_api_key.py
# Copy the generated key to config.py (API_KEY setting)

# 4. Initialize database
python -c "from backend.models import init_db; init_db()"

# 5. Start the backend
FLASK_APP=backend/app.py flask run --host=127.0.0.1

# 6. Load the browser extension (see below)
```

## Project Structure

```
SearchSift/
├── extension/                 # Browser extension (MV3)
│   ├── manifest.json
│   ├── background.js          # Service worker
│   ├── content_script.js      # Search detection
│   ├── popup.html             # Extension popup
│   ├── popup.js
│   └── options.html           # Settings page
├── backend/
│   ├── app.py                 # Flask application
│   ├── models.py              # SQLite schema
│   ├── categorizer.py         # Rule-based + ML categorization
│   ├── tasks.py               # Daily report generation
│   ├── config.py              # Configuration
│   └── ui/
│       └── templates/         # Jinja templates
├── reports/                   # Generated HTML/CSV reports
├── logs/                      # Application logs
├── scripts/
│   ├── generate_api_key.py
│   └── import_sample.py       # Sample data importer
├── tests/                     # Pytest tests
├── data/
│   └── sample_data.json       # Sample dataset
├── requirements.txt
├── Dockerfile
└── README.md
```

## Loading the Extension

### Chrome / Edge

1. Open `chrome://extensions/` (or `edge://extensions/`)
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `extension/` folder
5. Click the extension icon and enter your API key (same as in `config.py`)

### Firefox

Firefox requires slight modifications to the manifest. See [Firefox Notes](#firefox-notes) below.

1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `extension/manifest_firefox.json`

## Configuration

Edit `backend/config.py`:

```python
# API key for extension authentication
API_KEY = "your-generated-key-here"

# Backend settings
HOST = "127.0.0.1"
PORT = 5000

# CORS - extension origin (Chrome extension ID)
ALLOWED_ORIGINS = [
    "chrome-extension://YOUR_EXTENSION_ID",
    "moz-extension://YOUR_EXTENSION_ID",
]

# Categorization
ENABLE_SPACY = False  # Set True if spaCy is installed
```

## Running Daily Reports

### Manual
```bash
# Generate report for a specific date
python backend/tasks.py --run-once --date 2024-01-15

# Generate report for yesterday
python backend/tasks.py --run-once
```

### Scheduled (cron)
```bash
# Add to crontab (runs daily at 1 AM)
0 1 * * * cd /path/to/SearchSift && .venv/bin/python backend/tasks.py --run-once
```

### Using APScheduler (built-in)
```bash
# Run with scheduler enabled
python backend/tasks.py --scheduler
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ingest` | POST | Receive search events from extension |
| `/api/summary` | GET | Aggregated counts by category |
| `/report/daily` | GET | HTML report for a date |
| `/report/csv` | GET | CSV export for a date |
| `/` | GET | Dashboard UI |

### Example: Get Summary
```bash
curl "http://127.0.0.1:5000/api/summary?start=2024-01-01&end=2024-01-31"
```

## Sample Data

Import sample data for testing:
```bash
python scripts/import_sample.py
```

Then generate a report:
```bash
python backend/tasks.py --run-once --date 2024-01-15
```

## Running Tests

```bash
pytest tests/ -v
```

## Optional: HTTPS with Self-Signed Certificate

For HTTPS (useful if you want to access from other local devices):

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/key.pem -out certs/cert.pem \
  -days 365 -subj "/CN=localhost"

# Run with HTTPS
flask run --host=127.0.0.1 --cert=certs/cert.pem --key=certs/key.pem
```

Update extension's `background.js` to use `https://127.0.0.1:5000` and accept self-signed cert.

## Firefox Notes

Firefox uses Manifest V2 syntax for some features. Create `manifest_firefox.json`:

1. Change `"manifest_version": 3` to `"manifest_version": 2`
2. Replace `"service_worker"` with `"scripts"` in background:
   ```json
   "background": {
     "scripts": ["background.js"]
   }
   ```
3. Replace `"action"` with `"browser_action"`
4. Firefox doesn't need `host_permissions` separately - include in `permissions`
5. Use `browser.*` APIs instead of `chrome.*` (or use the WebExtension polyfill)

The content script works identically in both browsers.

## Security Notes

- **Local-only by default**: Backend binds to `127.0.0.1` only
- **API key required**: All `/ingest` requests must include `X-API-Key` header
- **CORS restricted**: Only allowed extension origins can make requests
- **No external calls**: Categorization is local (rule-based or spaCy)
- **Minimal data capture**: Only queries, URLs, timestamps, and engine names
- **No keystroke logging**: Only captures form submissions and link clicks

## Privacy

SearchSift captures:
- Search query text
- Clicked result URLs
- Search engine name
- Timestamps
- Tab/window IDs (for deduplication)

SearchSift does NOT capture:
- Page content or HTML
- Keystrokes
- Browsing history outside search engines
- Personal information beyond search queries

All data stays local in your SQLite database.

## Troubleshooting

### Extension not connecting
1. Check backend is running: `curl http://127.0.0.1:5000/health`
2. Verify API key matches in extension options and `config.py`
3. Check extension console for errors (right-click extension icon > Inspect)

### No searches captured
1. Ensure content script is loaded (check extension details > "Inspect views")
2. Verify search engine URL matches patterns in manifest
3. Check `logs/searchsift.log` for errors

### spaCy not working
```bash
pip install spacy
python -m spacy download en_core_web_sm
# Then set ENABLE_SPACY = True in config.py
```

## License

MIT License - See LICENSE file
