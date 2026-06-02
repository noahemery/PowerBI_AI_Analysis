# ============================================================
# ALLTECH JUMBOTRON CONFIG
# Change DATA_SOURCE to switch between scenarios
# ============================================================

# --- SCENARIO SELECTOR ---
# "pdf"          Scenario C/F: reads PDFs from PDF_DIR (works today)
# "database"     Scenario A/B: direct DB connection via gateway
# "powerbi_api"  Scenario D:   Power BI REST API (needs Azure AD app)
# "csv"          Scenario E:   flat files on network share / SharePoint
DATA_SOURCE = "pdf"

# --- HOURS OF OPERATION ---
OPERATING_HOURS = (6, 19)  # 6am to 7pm only

# --- PATHS ---
PDF_DIR         = "./data"
SUMMARY_OUTPUT  = "./display/summary.json"

# --- STOP LOSS ---
DAILY_SPEND_LIMIT   = 1.00   # max dollars per day before AI calls stop
COST_PER_API_CALL   = 0.10   # rough estimate per Claude call

# --- POLLING ---
POLL_INTERVAL_SECONDS = 1800   # how often the main loop runs (30 min)
CHANGE_THRESHOLD      = 0.05  # 5% shift in any key metric triggers AI rewrite

# --- DATABASE (Scenario A / B) ---
# Swap in your connection string after the IT meeting Wednesday
# SQL Server example:  "mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+17+for+SQL+Server"
# Oracle example:      "oracle+cx_oracle://user:pass@host:1521/service"
# PostgreSQL example:  "postgresql://user:pass@host/db"
DB_CONNECTION_STRING = ""

# SQL that returns one row per product per shift with key KPIs
# Adjust column names to match whatever Alltech's schema actually uses
DB_QUERY = """
    SELECT
        product_name,
        shift,
        shift_date,
        bfw_pct,
        oee_pct,
        avg_loading_time_min,
        loaded_kg,
        expected_kg,
        bag_hang_success_pct,
        bulk_density_lb_ft3
    FROM production_metrics
    WHERE shift_date = CAST(GETDATE() AS DATE)
    ORDER BY shift_date DESC, shift DESC
"""

# --- POWER BI REST API (Scenario D) ---
POWERBI_WORKSPACE_ID = ""
POWERBI_DATASET_ID   = ""
POWERBI_REPORT_ID    = ""
AZURE_TENANT_ID      = ""
AZURE_CLIENT_ID      = ""
AZURE_CLIENT_SECRET  = ""

# --- CSV / FLAT FILE (Scenario E) ---
# Can be a local path or a mounted network share
CSV_PATH = "./data/latest_shift.csv"

# --- DISPLAY ---
POWERBI_EMBED_URL = ""   # paste the Power BI "Publish to web" embed URL here
                         # or leave blank - display page handles it gracefully
