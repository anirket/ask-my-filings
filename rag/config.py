COLLECTION_NAME='FILINGS_CTX_PERIOD'   # 'FILINGS' = baseline, 'FILINGS_CTX' = context header without the period
BATCH=50
PREFETCH_LIMIT = 30

COMPANY_NAMES = {
    "RELIANCE": "Reliance Industries",
    "BHARTIARTL": "Bharti Airtel",
    "JPL": "Jio Platforms",
    "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank",
    "SBIN": "State Bank of India",
    "TCS": "Tata Consultancy Services",
    "BAJFINANCE": "Bajaj Finance",
    "LICI": "Life Insurance Corporation of India (LIC)",
    "INFY": "Infosys",
    "NSE": "National Stock Exchange of India",
}

# calendar period each fiscal quarter ends in (matches how questions are phrased: "quarter ended September 2026")
# NEW QUARTER ARRIVES (e.g. FY27-Q3 in January)? Add a line here, or indexing stops with a KeyError.
QUARTER_PERIOD = {
    "FY26-Q2": "September 2025",
    "FY26-Q3": "December 2025",
    "FY26-Q4": "March 2026",
    "FY27-Q1": "June 2026",
    "FY27-Q2": "September 2026",
}
