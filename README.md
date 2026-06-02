# Alltech KY System-2 Jumbotron Monitor

## Quick start (today — PDF mode)

```bash
pip install -r requirements.txt
# Drop PDF exports into ./data/
python main.py
# Open display/index.html in fullscreen browser
```

---

## Switching scenarios

Edit the single line in `config.py`:

| Scenario | DATA_SOURCE | What else to fill in |
|---|---|---|
| C/F — PDF exports (today) | `"pdf"` | Drop PDFs into `./data/` |
| A/B — Direct DB after gateway | `"database"` | `DB_CONNECTION_STRING`, `DB_QUERY` |
| D — Power BI REST API | `"powerbi_api"` | Azure AD fields in config |
| E — CSV / flat file | `"csv"` | `CSV_PATH` |

That's it. Everything else (change detection, summarizer, display) stays the same.

---

## Adding the Power BI embed

1. In Power BI Service: File → Embed report → Website or portal → copy the iframe URL
2. Paste it into `config.py → POWERBI_EMBED_URL`
3. The display page picks it up on next browser refresh

---

## Automation (Windows Task Scheduler)

1. Open Task Scheduler → Create Basic Task
2. Trigger: At startup, repeat every 5 minutes
3. Action: `python.exe C:\path\to\alltech_jumbotron\main.py`
4. Check "Run whether user is logged on or not"

---

## File structure

```
alltech_jumbotron/
├── config.py          ← one file to configure everything
├── main.py            ← run this
├── data_fetcher.py    ← data source abstraction
├── change_detector.py ← diff logic
├── summarizer.py      ← Claude API calls
├── requirements.txt
├── data/              ← drop PDF exports here
└── display/
    ├── index.html     ← open this on the jumbotron
    └── summary.json   ← written by main.py, read by the page
```
