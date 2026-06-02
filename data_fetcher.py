# ============================================================
# DATA FETCHER
# One function per scenario. fetch_latest() always returns the
# same shape so the rest of the pipeline never needs to change.
# ============================================================

import os
import glob
import json
import time
from config import (
    DATA_SOURCE, PDF_DIR, DB_CONNECTION_STRING, DB_QUERY,
    CSV_PATH, POWERBI_WORKSPACE_ID, POWERBI_DATASET_ID,
    AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
)


def fetch_latest():
    """
    Entry point. Returns a dict:
    {
        "source_type": "pdf" | "database" | "powerbi_api" | "csv",
        "source_label": str,          # filename or timestamp
        "raw_images": [...],          # list of PIL Images (for Claude vision)
        "structured": {...} | None,   # parsed metrics if available (DB/CSV)
        "fetched_at": float           # epoch timestamp
    }
    Returns None if no data is available yet.
    """
    if DATA_SOURCE == "pdf":
        return _fetch_pdf()
    elif DATA_SOURCE == "database":
        return _fetch_database()
    elif DATA_SOURCE == "powerbi_api":
        return _fetch_powerbi_api()
    elif DATA_SOURCE == "csv":
        return _fetch_csv()
    else:
        raise ValueError(f"Unknown DATA_SOURCE: {DATA_SOURCE}")


# ------------------------------------------------------------
# SCENARIO C / F  —  PDF files
# Works today with the exports you already have.
# When the gateway goes live, just change DATA_SOURCE in config.
# ------------------------------------------------------------
def _fetch_pdf():
    from pdf2image import convert_from_path

    pdfs = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    if not pdfs:
        print(f"  [pdf] No PDFs found in {PDF_DIR}")
        return None

    latest = pdfs[-1]
    print(f"  [pdf] Reading {os.path.basename(latest)}")

    pages = convert_from_path(latest, dpi=150, poppler_path=r"C:\poppler-26.02.0\Library\bin")

    return {
        "source_type": "pdf",
        "source_label": os.path.basename(latest),
        "raw_images": pages,
        "structured": None,          # no structured data in image-based PDFs
        "fetched_at": time.time(),
        "_meta": {"path": latest, "mtime": os.path.getmtime(latest)}
    }


# ------------------------------------------------------------
# SCENARIO A / B  —  Direct database connection
# Requires DB_CONNECTION_STRING in config.py.
# Install: pip install sqlalchemy pyodbc (SQL Server)
#          pip install sqlalchemy cx_Oracle (Oracle)
# ------------------------------------------------------------
def _fetch_database():
    from sqlalchemy import create_engine, text
    import pandas as pd

    if not DB_CONNECTION_STRING:
        raise RuntimeError("DB_CONNECTION_STRING is empty — fill it in config.py")

    print("  [database] Querying production metrics...")
    engine = create_engine(DB_CONNECTION_STRING)

    with engine.connect() as conn:
        df = pd.read_sql(text(DB_QUERY), conn)

    structured = _dataframe_to_metrics(df)

    return {
        "source_type": "database",
        "source_label": f"DB query @ {time.strftime('%H:%M')}",
        "raw_images": [],            # no images needed — Claude gets structured data
        "structured": structured,
        "fetched_at": time.time(),
        "_meta": {"row_count": len(df)}
    }


# ------------------------------------------------------------
# SCENARIO D  —  Power BI REST API
# Requires Azure AD app registration (ask IT for client_id/secret).
# Triggers a dataset refresh, then pulls export data.
# Install: pip install msal requests
# ------------------------------------------------------------
def _fetch_powerbi_api():
    #This is for Scenario D, which is Power BI REST API. It requires 
    # an Azure AD app registration and uses the msal library to authenticate 
    # and requests to call the Power BI API.
    import msal
    import requests

    if not AZURE_CLIENT_ID:
        raise RuntimeError("AZURE_CLIENT_ID is empty — fill in config.py after IT sets up Azure AD app")

    # Get access token
    app = msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}",
        client_credential=AZURE_CLIENT_SECRET
    )
    token = app.acquire_token_for_client(["https://analysis.windows.net/powerbi/api/.default"])
    headers = {"Authorization": f"Bearer {token['access_token']}"}

    # Trigger dataset refresh
    print("  [powerbi_api] Triggering dataset refresh...")
    requests.post(
        f"https://api.powerbi.com/v1.0/myorg/groups/{POWERBI_WORKSPACE_ID}/datasets/{POWERBI_DATASET_ID}/refreshes",
        headers=headers
    )

    # Wait briefly for refresh to complete (adjust as needed)
    time.sleep(30)

    # Pull dataset rows via DAX query
    print("  [powerbi_api] Fetching data...")
    resp = requests.post(
        f"https://api.powerbi.com/v1.0/myorg/groups/{POWERBI_WORKSPACE_ID}/datasets/{POWERBI_DATASET_ID}/executeQueries",
        headers=headers,
        json={"queries": [{"query": "EVALUATE 'ProductionMetrics'"}], "serializerSettings": {"includeNulls": True}}
    )
    rows = resp.json()["results"][0]["tables"][0]["rows"]

    return {
        "source_type": "powerbi_api",
        "source_label": f"Power BI API @ {time.strftime('%H:%M')}",
        "raw_images": [],
        "structured": {"rows": rows},
        "fetched_at": time.time(),
        "_meta": {"row_count": len(rows)}
    }


# ------------------------------------------------------------
# SCENARIO E  —  CSV / flat file (SharePoint, network share, etc.)
# No gateway needed if the file is on OneDrive/SharePoint.
# ------------------------------------------------------------
def _fetch_csv():
    import pandas as pd

    if not os.path.exists(CSV_PATH):
        print(f"  [csv] File not found: {CSV_PATH}")
        return None

    print(f"  [csv] Reading {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    structured = _dataframe_to_metrics(df)

    return {
        "source_type": "csv",
        "source_label": os.path.basename(CSV_PATH),
        "raw_images": [],
        "structured": structured,
        "fetched_at": time.time(),
        "_meta": {"mtime": os.path.getmtime(CSV_PATH), "row_count": len(df)}
    }


# ------------------------------------------------------------
# Shared helper — convert a DataFrame of production rows into
# the flat metrics dict the change detector and summarizer expect.
# Adjust column names to match your actual schema.
# ------------------------------------------------------------
def _dataframe_to_metrics(df):
    numeric_cols = df.select_dtypes("number").columns
    means = df[numeric_cols].mean().to_dict()

    return {
        "bfw_avg":              means.get("bfw_pct", 0),
        "oee_avg":              means.get("oee_pct", 0),
        "loading_time_avg":     means.get("avg_loading_time_min", 0),
        "loaded_vs_expected":   means.get("loaded_kg", 0) / max(means.get("expected_kg", 1), 1),
        "bag_hang_success_avg": means.get("bag_hang_success_pct", 0),
        "bulk_density_avg":     means.get("bulk_density_lb_ft3", 0),
        "row_count":            len(df)
    }
