import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable

st.set_page_config(page_title="NSE AI Market Lab", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp{background:#0b1020}
[data-testid="stHeader"]{background:rgba(11,16,32,.85)}
.block-container{max-width:1500px;padding-top:1.3rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:#10182b;border-right:1px solid #24314b}
[data-testid="stMetric"]{background:linear-gradient(145deg,#151f35,#111a2d);border:1px solid #263653;border-radius:14px;padding:14px}
[data-testid="stMetricLabel"]{color:#a9b8d0}
[data-testid="stMetricValue"]{color:#f4f7ff}
.hero{background:linear-gradient(115deg,#172846,#14213b 55%,#1b2944);border:1px solid #2b4166;border-radius:20px;padding:22px 26px;margin-bottom:16px}
.hero-kicker{color:#9db9e8;font-size:.76rem;letter-spacing:.12em;font-weight:700}
.hero h1{color:#f4f7ff;margin:7px 0 4px;font-size:2rem}
.hero p{color:#bdcbe0;margin:0}
.small-muted{color:#9aabc4;font-size:.85rem}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<div class="hero-kicker">INDIA • MARKET EDUCATION • HISTORICAL RESEARCH</div>
<h1>🇮🇳 NSE AI Market Lab</h1>
<p>One learning workspace for market structure, company research, sector context and financial literacy.</p>
</div>
""", unsafe_allow_html=True)

st.warning("EDUCATIONAL USE ONLY • Data may be delayed, incomplete or unavailable. This app does not provide stock picks, buy/sell signals, forecasts, F&O strategies, trade targets, broker connections or real orders.")

# Broad sample universe for educational comparisons; not a recommendation list.
SECTOR_UNIVERSE = {
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS"],
    "Information Technology": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS"],
    "Automobiles": ["MARUTI.NS", "M&M.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS"],
    "Consumer": ["ITC.NS", "HINDUNILVR.NS", "TITAN.NS", "ASIANPAINT.NS"],
    "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
    "Industrials": ["LT.NS", "SIEMENS.NS", "BEL.NS", "HAL.NS"],
}

INDEX_SYMBOLS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
}

@st.cache_data(ttl=900, show_spinner=False)
def get_history(symbol, period, interval):
    data = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna(how="all")

@st.cache_data(ttl=1800, show_spinner=False)
def get_company_profile(symbol):
    try:
        info = yf.Ticker(symbol).info
        if not isinstance(info, dict):
            return {}
        return info
    except Exception:
        return {}

@st.cache_data(ttl=900, show_spinner=False)
def get_company_news(symbol):
    try:
        return yf.Ticker(symbol).news or []
    except Exception:
        return []

@st.cache_data(ttl=900, show_spinner=False)
def get_sector_history(period):
    """Build sector averages from available sample tickers, tolerating yfinance column-layout changes."""
    symbols = sorted(set(s for group in SECTOR_UNIVERSE.values() for s in group))
    close = pd.DataFrame()

    try:
        raw = yf.download(
            symbols, period=period, interval="1d", auto_adjust=True,
            progress=False, threads=False, group_by="column"
        )
        if not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                # yfinance versions may return either (Price, Ticker) or (Ticker, Price).
                if "Close" in raw.columns.get_level_values(0):
                    close = raw["Close"].copy()
                elif "Close" in raw.columns.get_level_values(1):
                    close = raw.xs("Close", axis=1, level=1).copy()
            elif "Close" in raw.columns:
                close = raw[["Close"]].copy()
                if len(symbols) == 1:
                    close.columns = symbols
    except Exception:
        close = pd.DataFrame()

    # Fallback: fetch symbols individually if the batch response was empty or unusable.
    if close.empty:
        pieces = {}
        for ticker in symbols:
            try:
                one = yf.download(
                    ticker, period=period, interval="1d", auto_adjust=True,
                    progress=False, threads=False
                )
                if one.empty:
                    continue
                if isinstance(one.columns, pd.MultiIndex):
                    if "Close" in one.columns.get_level_values(0):
                        series = one["Close"]
                        if isinstance(series, pd.DataFrame):
                            series = series.iloc[:, 0]
                    elif "Close" in one.columns.get_level_values(1):
                        series = one.xs("Close", axis=1, level=1).iloc[:, 0]
                    else:
                        continue
                elif "Close" in one.columns:
                    series = one["Close"]
                else:
                    continue
                series = pd.to_numeric(series, errors="coerce").dropna()
                if not series.empty:
                    pieces[ticker] = series
            except Exception:
                continue
        if pieces:
            close = pd.DataFrame(pieces)

    if close.empty:
        return pd.DataFrame()

    # Normalize possible duplicate or unexpected column labels.
    close = close.loc[:, ~close.columns.duplicated()]
    rows = []
    for sector, names in SECTOR_UNIVERSE.items():
        changes = []
        for ticker in names:
            if ticker not in close.columns:
                continue
            series = pd.to_numeric(close[ticker], errors="coerce").dropna()
            if len(series) > 1 and float(series.iloc[0]) != 0:
                changes.append((float(series.iloc[-1]) / float(series.iloc[0]) - 1) * 100)
        if changes:
            rows.append({
                "Sector": sector,
                "Average historical change (%)": sum(changes) / len(changes),
                "Companies with data": len(changes)
            })
    return pd.DataFrame(rows)

with st.sidebar:
    st.markdown("## 🧭 Navigation")
    selected_symbol = st.text_input("Company ticker", value="RELIANCE.NS", help="Examples: RELIANCE.NS, TCS.NS, INFY.NS, SBIN.NS")
    period = st.selectbox("Historical comparison period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    interval = st.selectbox("Chart interval", ["1d", "1wk", "1mo"], index=0)
    st.caption("Source: Yahoo Finance unofficial data. Cross-check important facts with NSE filings and company disclosures.")
    st.divider()
    st.markdown("**Official learning links**")
    st.markdown("[NSE India reports](https://www.nseindia.com/report-detail)")
    st.markdown("[SEBI Investor](https://investor.sebi.gov.in/)")
    st.markdown("[SEBI learning material](https://investor.sebi.gov.in/iematerial.html)")

symbol = selected_symbol.strip().upper()
if not symbol:
    symbol = "RELIANCE.NS"

tab_names = ["🌐 Market overview", "🗺️ Sector map", "🏢 Company in one view", "📊 Historical charts", "🧠 Research desk", "🧹 Data quality lab", "📚 Learning centre", "🧪 Classroom lab", "📝 Research report builder"]
tabs = st.tabs(tab_names)

# Market overview
with tabs[0]:
    st.subheader("Market snapshot")
    st.caption("Index history is shown for context. It is not a live exchange feed.")
    cols = st.columns(4)
    for col, (label, ticker) in zip(cols, INDEX_SYMBOLS.items()):
        try:
            hist = get_history(ticker, "5d", "1d")
            if not hist.empty and "Close" in hist:
                vals = hist["Close"].dropna()
                last = float(vals.iloc[-1])
                delta = ((last / float(vals.iloc[-2])) - 1) * 100 if len(vals) > 1 and vals.iloc[-2] else 0
                col.metric(label, f"{last:,.2f}", f"{delta:+.2f}%")
            else:
                col.metric(label, "Unavailable")
        except Exception:
            col.metric(label, "Unavailable")
    st.markdown("### Selected company historical overview")
    hist = get_history(symbol, period, interval)
    if not hist.empty and "Close" in hist:
        close = hist["Close"].astype(float).dropna()
        if not close.empty:
            a, b, c, d = st.columns(4)
            a.metric("Latest available close", f"₹{float(close.iloc[-1]):,.2f}")
            change = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100 if len(close) > 1 and close.iloc[0] else 0
            b.metric("Selected-period change", f"{change:+.2f}%")
            c.metric("Period high", f"₹{float(hist['High'].max()):,.2f}")
            d.metric("Period low", f"₹{float(hist['Low'].min()):,.2f}")
            st.caption(f"{len(hist):,} observations • {hist.index.min().date()} to {hist.index.max().date()} • {period} • {interval}")
        else:
            st.info("No closing-price values are available for this selection.")
    else:
        st.info("Historical data is not available for this ticker right now. Check the symbol or try again later.")

# Sector map
with tabs[1]:
    st.subheader("Sector comparison map")
    st.write("A broad educational sample of companies grouped by sector. Values are average historical changes over the selected period, not a complete exchange-wide heatmap.")
    try:
        sector_df = get_sector_history(period)
        if not sector_df.empty:
            # Symmetric scale keeps positive and negative sector moves visually balanced.
            # Red = negative historical change; green = positive; near-white = around zero.
            color_limit = max(float(sector_df["Average historical change (%)"].abs().max()), 1.0)
            fig = px.treemap(
                sector_df,
                path=["Sector"],
                values="Companies with data",
                color="Average historical change (%)",
                color_continuous_scale=[
                    [0.00, "#991b1b"],
                    [0.18, "#dc2626"],
                    [0.36, "#fca5a5"],
                    [0.50, "#f8fafc"],
                    [0.64, "#86efac"],
                    [0.82, "#22c55e"],
                    [1.00, "#166534"],
                ],
                range_color=(-color_limit, color_limit),
                color_continuous_midpoint=0,
                hover_data={"Average historical change (%)":":.2f","Companies with data":True},
                title=f"Sector performance • {period} historical window",
            )
            fig.update_traces(
                texttemplate="%{label}<br>%{color:.2f}%",
                textfont=dict(color="#0b1020", size=14),
                marker=dict(line=dict(color="#0b1020", width=3)),
                tiling=dict(packing="squarify", pad=4),
            )
            fig.update_coloraxes(
                colorbar=dict(
                    title=dict(text="Historical change", font=dict(color="#e5e7eb")),
                    ticksuffix="%",
                    tickfont=dict(color="#e5e7eb"),
                    outlinecolor="#64748b",
                )
            )
            fig.update_layout(
                template="plotly_dark",
                height=560,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                title_font=dict(size=19, color="#f8fafc"),
                margin=dict(l=8, r=8, t=55, b=8),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(sector_df.sort_values("Average historical change (%)", ascending=False), hide_index=True, use_container_width=True)
        else:
            st.info("Sector sample data could not be loaded. Try again later.")
    except Exception as error:
        st.warning("Sector data could not be processed on this refresh. The data provider may be temporarily unavailable or may have changed its response format.")
        with st.expander("Technical details"):
            st.code(str(error))
    st.caption("Coverage is limited to the sample tickers listed in the app. Missing companies do not mean a sector was inactive.")

# Company one view
with tabs[2]:
    st.subheader(f"{symbol} • Company research page")
    profile = get_company_profile(symbol)
    hist = get_history(symbol, period, "1d")
    if profile:
        company_name = profile.get("longName") or profile.get("shortName") or symbol
        st.markdown(f"### {company_name}")
        st.caption("Company profile fields are supplied by an unofficial third-party data source and may be missing or outdated.")
        x1, x2, x3 = st.columns(3)
        x1.metric("Sector", profile.get("sector") or "Not available")
        x2.metric("Industry", profile.get("industry") or "Not available")
        x3.metric("Website", "Available" if profile.get("website") else "Not listed")
        summary = profile.get("longBusinessSummary")
        if summary:
            with st.expander("Business description", expanded=True):
                st.write(summary)
        st.markdown("### Company facts")
        facts = {
            "Exchange": profile.get("exchange"),
            "Currency": profile.get("currency"),
            "Country": profile.get("country"),
            "Employees": profile.get("fullTimeEmployees"),
            "Website": profile.get("website"),
        }
        facts_df = pd.DataFrame([{"Field": k, "Value": v} for k, v in facts.items() if v not in (None, "")])
        if not facts_df.empty:
            st.dataframe(facts_df, hide_index=True, use_container_width=True)
        if profile.get("website"):
            st.markdown(f"[Open company website]({profile.get('website')})")
    else:
        st.info("Company profile information is unavailable from the data provider for this ticker.")
    st.markdown("### Historical price context")
    if not hist.empty:
        st.line_chart(hist["Close"], height=230)
        st.caption("Historical prices are descriptive only and do not predict future performance.")
    st.markdown("### Recent company-related headlines")
    news = get_company_news(symbol)
    shown = 0
    for item in news[:12]:
        item = item.get("content", item) if isinstance(item, dict) else {}
        title = item.get("title") or item.get("headline")
        canonical = item.get("canonicalUrl") or item.get("link") or {}
        url = canonical.get("url") if isinstance(canonical, dict) else canonical
        publisher = item.get("publisher") or (item.get("provider", {}).get("displayName") if isinstance(item.get("provider"), dict) else None)
        if title and url:
            st.markdown(f"- [{title}]({url})")
            if publisher:
                st.caption(publisher)
            shown += 1
    if shown == 0:
        st.caption("No headlines were returned. Use official company announcements and exchange filings for verification.")
    st.markdown("[Find official NSE company filings](https://www.nseindia.com/companies-listing/corporate-filings-announcements)")

# Historical charts
with tabs[3]:
    st.subheader("Historical chart laboratory")
    hist = get_history(symbol, period, interval)
    if not hist.empty and {"Open", "High", "Low", "Close"}.issubset(hist.columns):
        close = hist["Close"].astype(float)
        chart_mode = st.radio("Visualisation", ["Candlestick", "Closing-price line"], horizontal=True, key="chart_mode")
        fig = go.Figure()
        if chart_mode == "Candlestick":
            fig.add_trace(go.Candlestick(x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"], name="Historical price"))
        else:
            fig.add_trace(go.Scatter(x=hist.index, y=close, mode="lines", name="Close"))
        fig.add_trace(go.Scatter(x=hist.index, y=close.rolling(20).mean(), mode="lines", name="20-observation average", line=dict(dash="dot")))
        fig.update_layout(height=480, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=8,r=8,t=25,b=8), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        if "Volume" in hist:
            st.markdown("### Historical volume")
            st.bar_chart(hist["Volume"], height=200)
        st.download_button("Download displayed history (CSV)", hist.to_csv().encode("utf-8"), file_name=f"{symbol.replace('.', '_')}_history.csv", mime="text/csv")
    else:
        st.info("Chart data is unavailable for this symbol and interval.")

# Research desk
with tabs[4]:
    st.subheader("Multi-role research desk")
    st.caption("These explainers use historical data and public information. They are not autonomous agents and do not issue trade instructions.")
    hist = get_history(symbol, period, "1d")
    if not hist.empty and "Close" in hist:
        close = hist["Close"].astype(float).dropna()
        if len(close) > 1:
            change = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100
            daily = close.pct_change().dropna()
            vol = float(daily.std() * (252 ** 0.5) * 100) if len(daily) > 1 else 0
            points = [
                ("1 · Data quality reviewer", f"Loaded {len(hist)} observations. Check missing dates, outliers, adjusted-price methodology and source reliability."),
                ("2 · Historical performance explainer", f"The selected sample changed by {change:+.2f}% between its first and last close. This is a description of that sample, not a forecast."),
                ("3 · Risk-literacy educator", f"Simple annualised historical volatility estimate: {vol:.1f}%. Volatility measures variation in past returns, not the probability of a particular outcome."),
                ("4 · Sector-context researcher", "Compare the company with its sector and broad indices. Different business models and market conditions can make comparisons imperfect."),
                ("5 · Skeptical reviewer", "Ask what information is missing, whether the selected dates are unusual, and whether the data provider has revised or omitted observations."),
                ("6 · Corporate-disclosure reader", "Read company announcements, annual reports, financial results and exchange filings before drawing conclusions from a chart."),
                ("7 · News-context reviewer", "Headlines can be incomplete or sensational. Open the original publisher link, check its date, and distinguish reported facts from commentary."),
                ("8 · Bias checker", "Watch for confirmation bias, recency bias, survivorship bias and social-media claims that show selected wins without a complete record.")
            ]
            for heading, explanation in points:
                with st.expander(heading, expanded=False):
                    st.write(explanation)
        else:
            st.info("More historical observations are needed for this research summary.")
    else:
        st.info("Load historical data to use the research desk.")
    st.warning("No stock recommendations, entry/exit levels, F&O strategies, targets or stop-loss values are generated.")


# Data quality lab
with tabs[5]:
    st.subheader("Historical data quality audit")
    st.caption("A transparent set of checks on the downloaded observations. These checks do not certify the provider or guarantee that the data is correct.")
    audit = get_history(symbol, period, interval)
    if audit.empty:
        st.info("No historical observations are available for this ticker and interval. Try another symbol or refresh later.")
    else:
        checks = []
        required = ["Open", "High", "Low", "Close"]
        missing_columns = [column for column in required if column not in audit.columns]
        checks.append({
            "Check": "Required OHLC columns",
            "Result": "PASS" if not missing_columns else "REVIEW",
            "Details": "All present" if not missing_columns else "Missing: " + ", ".join(missing_columns)
        })
        duplicate_count = int(audit.index.duplicated().sum())
        checks.append({"Check": "Duplicate timestamps", "Result": "PASS" if duplicate_count == 0 else "REVIEW", "Details": f"{duplicate_count} duplicate rows"})
        missing_cells = int(audit[required].isna().sum().sum()) if not missing_columns else int(audit.isna().sum().sum())
        checks.append({"Check": "Missing price values", "Result": "PASS" if missing_cells == 0 else "REVIEW", "Details": f"{missing_cells} missing cells in available price columns"})
        if not missing_columns:
            invalid_ohlc = int(((audit["High"] < audit["Low"]) | (audit["High"] < audit["Open"]) | (audit["High"] < audit["Close"]) | (audit["Low"] > audit["Open"]) | (audit["Low"] > audit["Close"])).fillna(False).sum())
            nonpositive = int((audit[required] <= 0).any(axis=1).sum())
            checks.append({"Check": "OHLC range consistency", "Result": "PASS" if invalid_ohlc == 0 else "REVIEW", "Details": f"{invalid_ohlc} rows with inconsistent high/low ranges"})
            checks.append({"Check": "Positive price values", "Result": "PASS" if nonpositive == 0 else "REVIEW", "Details": f"{nonpositive} rows with zero or negative prices"})
        if "Volume" in audit.columns:
            negative_volume = int((audit["Volume"] < 0).fillna(False).sum())
            checks.append({"Check": "Non-negative volume", "Result": "PASS" if negative_volume == 0 else "REVIEW", "Details": f"{negative_volume} rows with negative volume"})
        audit_df = pd.DataFrame(checks)
        total_checks = len(audit_df)
        passed = int((audit_df["Result"] == "PASS").sum())
        reviewed = total_checks - passed
        q1, q2, q3 = st.columns(3)
        q1.metric("Observations", f"{len(audit):,}")
        q2.metric("Checks passed", f"{passed}/{total_checks}")
        q3.metric("Items to review", reviewed)
        st.dataframe(audit_df, hide_index=True, use_container_width=True)
        st.markdown("### Coverage details")
        c1, c2, c3 = st.columns(3)
        c1.metric("First observation", str(audit.index.min().date()))
        c2.metric("Last observation", str(audit.index.max().date()))
        c3.metric("Selected interval", interval)
        st.caption("This audit checks only the rows returned by Yahoo Finance. It cannot detect every corporate-action adjustment, survivorship bias, missing exchange session or incorrect source value.")
        st.download_button("Download data quality report (CSV)", audit_df.to_csv(index=False).encode("utf-8"), file_name=f"{symbol.replace('.', '_')}_data_quality.csv", mime="text/csv")

# Learning centre
with tabs[6]:
    st.subheader("Learning centre")
    lessons = {
        "Candlesticks": "A candle summarises open, high, low and close during one interval. The body shows the open-to-close range; the wicks show the interval extremes.",
        "Trading volume": "Volume counts shares traded during an interval. It adds context but does not explain the cause of a price move by itself.",
        "Moving averages": "A moving average smooths earlier observations. It is a historical summary, not a prediction.",
        "Volatility": "Volatility describes variation in returns. Historical volatility does not guarantee future outcomes.",
        "Diversification": "Diversification spreads exposure across different assets or sectors. It can reduce concentration but cannot remove every risk.",
        "Market indices": "An index tracks a defined group of securities using a published method. It represents that group, not the entire economy.",
        "Corporate actions": "Corporate actions include events such as dividends, splits, bonus issues, rights issues and buybacks.",
        "Financial statements": "The balance sheet, income statement and cash-flow statement describe different aspects of a company's financial position and activity.",
        "Market risk": "Market risk is the possibility that broad market or economic changes affect the value of securities.",
        "Liquidity risk": "Liquidity risk relates to difficulty buying or selling an asset promptly without a significant price impact.",
        "Backtesting limitations": "Backtests can be distorted by missing data, survivorship bias, overfitting, costs and changing market conditions.",
        "Social-media due diligence": "Check dates, original sources and full context. Do not rely on screenshots of selected profitable examples or anonymous claims."
    }
    topic = st.selectbox("Choose a lesson", list(lessons))
    st.info(lessons[topic])
    st.markdown("### Knowledge check")
    questions = [
        ("Does past performance guarantee future returns?", ["Yes", "No"], "No"),
        ("What does volume measure?", ["Shares traded", "Company profit", "Future price"], "Shares traded"),
        ("What is diversification intended to reduce?", ["All risk", "Concentration risk", "Inflation always"], "Concentration risk"),
        ("Where should company disclosures be verified?", ["Anonymous posts", "Official exchange/company sources", "Unverified screenshots"], "Official exchange/company sources"),
    ]
    if "quiz_answers" not in st.session_state:
        st.session_state.quiz_answers = {}
    for i, (question, options, answer) in enumerate(questions):
        st.session_state.quiz_answers[i] = st.radio(question, options, key=f"quiz_{i}")
    if st.button("Check my answers"):
        score = sum(st.session_state.quiz_answers.get(i) == q[2] for i, q in enumerate(questions))
        st.success(f"You got {score} out of {len(questions)} correct.")
    st.markdown("### Trusted learning resources")
    st.markdown("- [SEBI Investor education portal](https://investor.sebi.gov.in/)")
    st.markdown("- [SEBI reading material](https://investor.sebi.gov.in/iematerial.html)")
    st.markdown("- [SEBI video learning](https://investor.sebi.gov.in/inv_aware_edu_videos.html)")
    st.markdown("- [NSE reports and market information](https://www.nseindia.com/report-detail)")
    st.markdown("- [NISM investor awareness learning](https://www.nism.ac.in/sebi-investor-awareness-test/)")

# Classroom lab
with tabs[7]:
    st.subheader("Classroom portfolio • fictional points only")
    st.write("A learning simulation for recording made-up examples. It is not connected to a broker and does not use real money.")
    if "classroom_points" not in st.session_state:
        st.session_state.classroom_points = 10000
    if "classroom_notes" not in st.session_state:
        st.session_state.classroom_notes = []
    a, b = st.columns(2)
    a.metric("Starting virtual points", "10,000")
    b.metric("Current fictional points", f"{st.session_state.classroom_points:,}")
    with st.form("classroom_adjustment"):
        delta = st.number_input("Add or subtract fictional points", min_value=-10000, max_value=10000, value=0, step=100)
        note = st.text_input("Learning note (optional)")
        submitted = st.form_submit_button("Record classroom example")
    if submitted:
        st.session_state.classroom_points = max(0, st.session_state.classroom_points + int(delta))
        st.session_state.classroom_notes.append({"Change": int(delta), "Fictional points": st.session_state.classroom_points, "Note": note})
        st.success("Classroom example recorded.")
    if st.session_state.classroom_notes:
        st.dataframe(pd.DataFrame(st.session_state.classroom_notes), hide_index=True, use_container_width=True)
    if st.button("Reset classroom lab"):
        st.session_state.classroom_points = 10000
        st.session_state.classroom_notes = []
        st.success("Classroom lab reset.")


# Research report builder
with tabs[8]:
    st.subheader("Company research report builder")
    st.write("Create a polished PDF snapshot from the selected company's available profile, historical observations and returned headlines.")
    st.caption("This report is assembled from data currently available in the app. It is not an AI-generated assessment, an audit of the company, or a recommendation.")
    if st.button("Build professional PDF report", key="build_research_report"):
        with st.spinner("Collecting company information and designing your PDF..."):
            report_profile = get_company_profile(symbol)
            report_hist = get_history(symbol, period, "1d")
            report_news = get_company_news(symbol)

            company_name = (report_profile.get("longName") or report_profile.get("shortName") or symbol) if report_profile else symbol
            sector_name = report_profile.get("sector") or "Not available" if report_profile else "Not available"
            industry_name = report_profile.get("industry") or "Not available" if report_profile else "Not available"
            country_name = report_profile.get("country") or "Not available" if report_profile else "Not available"
            website_url = report_profile.get("website") or "" if report_profile else ""
            business_summary = report_profile.get("longBusinessSummary") or "A business description was not returned by the data provider." if report_profile else "Company profile information was unavailable from the data provider."

            report_close = pd.to_numeric(report_hist["Close"], errors="coerce").dropna() if not report_hist.empty and "Close" in report_hist.columns else pd.Series(dtype=float)
            observation_count = len(report_close)
            if observation_count:
                first_date = str(report_close.index.min().date())
                last_date = str(report_close.index.max().date())
                latest_close = float(report_close.iloc[-1])
                report_change = ((latest_close / float(report_close.iloc[0])) - 1) * 100 if observation_count > 1 and float(report_close.iloc[0]) else 0.0
            else:
                first_date = last_date = "Not available"
                latest_close = None
                report_change = None

            headline_items = []
            for news_item in report_news[:8]:
                news_item = news_item.get("content", news_item) if isinstance(news_item, dict) else {}
                headline = news_item.get("title") or news_item.get("headline")
                canonical = news_item.get("canonicalUrl") or news_item.get("link") or {}
                headline_url = canonical.get("url") if isinstance(canonical, dict) else canonical
                publisher_name = news_item.get("publisher") or (news_item.get("provider", {}).get("displayName") if isinstance(news_item.get("provider"), dict) else None)
                if headline:
                    headline_items.append((str(headline), str(publisher_name or "Publisher not listed"), str(headline_url or "")))

        pdf_buffer = BytesIO()
        page_width, page_height = A4
        navy = colors.HexColor("#14243D")
        blue = colors.HexColor("#2864A5")
        pale_blue = colors.HexColor("#EAF2FB")
        ink = colors.HexColor("#243247")
        muted = colors.HexColor("#66758A")
        light = colors.HexColor("#F4F7FB")
        teal = colors.HexColor("#167D83")
        orange = colors.HexColor("#C47724")

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, leading=29, textColor=colors.white, alignment=TA_LEFT, spaceAfter=5))
        styles.add(ParagraphStyle(name="ReportSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=15, textColor=colors.HexColor("#DCE8F5")))
        styles.add(ParagraphStyle(name="SectionHeadingCustom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=navy, spaceBefore=13, spaceAfter=7))
        styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=14, textColor=ink, spaceAfter=5))
        styles.add(ParagraphStyle(name="SmallCustom", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.5, leading=11, textColor=muted))
        styles.add(ParagraphStyle(name="CardLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=muted))
        styles.add(ParagraphStyle(name="CardValue", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=navy))
        styles.add(ParagraphStyle(name="NewsTitle", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=blue, spaceAfter=2))
        styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.5, leading=12, textColor=navy))
        
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#D9E2EF"))
            canvas.setLineWidth(0.6)
            canvas.line(18 * mm, 15 * mm, page_width - 18 * mm, 15 * mm)
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(muted)
            canvas.drawString(18 * mm, 10 * mm, "NSE AI Market Lab  |  Educational research only")
            canvas.drawRightString(page_width - 18 * mm, 10 * mm, f"Page {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            pdf_buffer, pagesize=A4,
            rightMargin=18 * mm, leftMargin=18 * mm,
            topMargin=17 * mm, bottomMargin=22 * mm,
            title=f"{company_name} - Educational Research Report",
            author="NSE AI Market Lab"
        )
        story = []

        cover = [
            [Paragraph("NSE AI MARKET LAB", ParagraphStyle("Brand", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#A9C7E8"), leading=12))],
            [Paragraph("Company Research<br/>Report", styles["ReportTitle"])],
            [Paragraph(f"{escape(company_name)}  |  {escape(symbol)}", styles["ReportSubtitle"])],
            [Paragraph(f"Prepared {datetime.now().strftime('%d %B %Y, %H:%M')}  •  Historical window: {escape(period)}", styles["ReportSubtitle"])]
        ]
        cover_table = Table(cover, colWidths=[page_width - 36 * mm], rowHeights=[12 * mm, 29 * mm, 13 * mm, 12 * mm])
        cover_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), navy),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([cover_table, Spacer(1, 8 * mm)])

        warning = Table([[Paragraph("<b>EDUCATIONAL USE ONLY</b><br/>This report is not investment advice. It does not provide stock picks, buy/sell signals, forecasts or trading instructions. Market data and company details may be delayed, incomplete or outdated. Verify important information using official company and exchange disclosures.", styles["Callout"])]], colWidths=[page_width - 36 * mm])
        warning.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF4DF")),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#E8C98C")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ]))
        story.append(warning)

        story.append(Paragraph("01  Company profile", styles["SectionHeadingCustom"]))
        profile_rows = [
            [Paragraph("SECTOR", styles["CardLabel"]), Paragraph("INDUSTRY", styles["CardLabel"]), Paragraph("COUNTRY", styles["CardLabel"])],
            [Paragraph(escape(str(sector_name)), styles["CardValue"]), Paragraph(escape(str(industry_name)), styles["CardValue"]), Paragraph(escape(str(country_name)), styles["CardValue"])]
        ]
        profile_table = Table(profile_rows, colWidths=[(page_width - 36 * mm) / 3] * 3)
        profile_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), pale_blue),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6E2F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6E2F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([profile_table, Spacer(1, 4 * mm), Paragraph("Business description", styles["BodyCustom"]), Paragraph(escape(str(business_summary)).replace("\n", "<br/>"), styles["BodyCustom"])])
        if website_url.startswith(("http://", "https://")):
            story.append(Paragraph(f'Company website: <link href="{escape(website_url, {chr(34): "&quot;"})}" color="#2864A5">{escape(website_url)}</link>', styles["SmallCustom"]))

        story.append(Paragraph("02  Historical data snapshot", styles["SectionHeadingCustom"]))
        if observation_count:
            metric_rows = [
                [Paragraph("OBSERVATIONS", styles["CardLabel"]), Paragraph("LATEST AVAILABLE CLOSE", styles["CardLabel"]), Paragraph("CHANGE IN SELECTED PERIOD", styles["CardLabel"])],
                [Paragraph(f"{observation_count:,}", styles["CardValue"]), Paragraph(f"INR {latest_close:,.2f}", styles["CardValue"]), Paragraph(f"{report_change:+.2f}%", styles["CardValue"])]
            ]
            metric_table = Table(metric_rows, colWidths=[(page_width - 36 * mm) / 3] * 3)
            metric_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), light),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DFE6EF")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DFE6EF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.extend([metric_table, Spacer(1, 3 * mm)])
            date_rows = [[Paragraph("<b>First available date</b>", styles["BodyCustom"]), Paragraph(escape(first_date), styles["BodyCustom"])],
                         [Paragraph("<b>Last available date</b>", styles["BodyCustom"]), Paragraph(escape(last_date), styles["BodyCustom"])]]
            date_table = Table(date_rows, colWidths=[55 * mm, page_width - 91 * mm])
            date_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#E4EAF2")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.extend([date_table, Paragraph("The percentage describes the first and last available closing observations in this dataset. It is not a forecast and does not account for every corporate action or data issue.", styles["SmallCustom"])])
        else:
            story.append(Paragraph("Historical closing-price data was unavailable for this selection.", styles["BodyCustom"]))

        story.append(Paragraph("03  Recent company-related headlines", styles["SectionHeadingCustom"]))
        if headline_items:
            for index, (headline, publisher, headline_url) in enumerate(headline_items, start=1):
                story.append(Paragraph(f"{index:02d}. {escape(headline)}", styles["NewsTitle"]))
                meta = escape(publisher)
                if headline_url.startswith(("http://", "https://")):
                    meta += f'  |  <link href="{escape(headline_url, {chr(34): "&quot;"})}" color="#2864A5">Open source article</link>'
                else:
                    meta += "  |  Link not provided"
                story.append(Paragraph(meta, styles["SmallCustom"]))
                story.append(Spacer(1, 2 * mm))
        else:
            story.append(Paragraph("No headlines with usable titles were returned. Check official company and exchange announcements for current information.", styles["BodyCustom"]))

        story.append(Paragraph("04  Researcher's verification checklist", styles["SectionHeadingCustom"]))
        checklist = [
            "Confirm company details using its official website and latest annual report.",
            "Verify financial results and corporate announcements on the exchange website.",
            "Check the date, publisher and original context of every headline.",
            "Look for missing observations, corporate actions and possible data-provider errors.",
            "Compare multiple reliable sources; do not rely on a single chart or headline."
        ]
        for item in checklist:
            story.append(Paragraph(f"&bull; {escape(item)}", styles["BodyCustom"]))

        story.append(Paragraph("Official learning and disclosure resources", styles["SectionHeadingCustom"]))
        story.append(Paragraph('<link href="https://www.nseindia.com/companies-listing/corporate-filings-announcements" color="#2864A5">NSE company filings and announcements</link>', styles["BodyCustom"]))
        story.append(Paragraph('<link href="https://investor.sebi.gov.in/" color="#2864A5">SEBI Investor education portal</link>', styles["BodyCustom"]))
        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#D9E2EF")))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Data source note: Historical market data, company profile fields and headlines are supplied by Yahoo Finance through yfinance. This is an unofficial source and may be delayed, incomplete, revised or unavailable. This report is a learning aid, not a complete company analysis.", styles["SmallCustom"]))

        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        pdf_bytes = pdf_buffer.getvalue()
        st.success("Your professionally formatted PDF report is ready.")
        st.download_button(
            "Download professional research report (PDF)",
            data=pdf_bytes,
            file_name=f"{symbol.replace('.', '_')}_educational_research_report.pdf",
            mime="application/pdf"
        )
        with st.expander("Report contents"):
            st.markdown("- Company profile and business description")
            st.markdown("- Historical data snapshot with key metrics")
            st.markdown("- Recent headlines with source links")
            st.markdown("- Verification checklist and official resources")
            st.markdown("- Educational-use disclaimer and page numbers")
    else:
        st.info("Select a company ticker in the sidebar, then click Build professional PDF report.")

st.divider()
st.caption("NSE AI Market Lab • Free-first learning project • Historical data can be delayed or incomplete • Not investment advice.")
