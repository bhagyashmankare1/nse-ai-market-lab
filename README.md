# NSE AI Market Lab — Starter

A Windows-friendly, free-first educational dashboard for exploring historical NSE/BSE price data.

## What is included
- Historical price and volume charts
- A descriptive 20-observation average overlay
- Five transparent educational research roles
- Beginner-friendly market concepts
- CSV export
- A classroom-only portfolio demo

## Safety and scope
This project is for education. It does not give buy/sell recommendations, forecasts, trade setups, stop-loss/target levels, broker connections, or real order execution. Yahoo Finance data is unofficial and may be delayed or incomplete.

## Requirements
- Windows 10/11
- Python 3.10 or newer
- Internet connection for historical data

## Install and run (Windows)
1. Install Python from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Extract this ZIP.
3. Open the extracted folder.
4. Double-click `install_and_run.bat`.
5. The app should open at `http://localhost:8501`.

If double-click does not work:
```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Example symbols
- `RELIANCE.NS`
- `TCS.NS`
- `INFY.NS`
- `SBIN.BO`

## Next development stages
1. Add a broad-market overview and sector education page.
2. Add a news reader with source links and neutral summaries.
3. Add company filing/document explainers.
4. Replace rule-based educational roles with optional local AI using Ollama, if the laptop can run it.
5. Add data-quality checks and tests.

Do not add broker credentials or connect this learning project to a real-money account.
