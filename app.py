import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="NSE AI Market Lab", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp {background:#0b1020;}
[data-testid="stHeader"] {background:rgba(11,16,32,.85);}
.block-container {max-width:1500px;padding-top:1.6rem;padding-bottom:3rem;}
[data-testid="stSidebar"] {background:#10182b;border-right:1px solid #24314b;}
[data-testid="stMetric"] {background:linear-gradient(145deg,#151f35,#111a2d);border:1px solid #263653;border-radius:15px;padding:16px 18px;}
[data-testid="stMetricLabel"] {color:#a9b8d0;}
[data-testid="stMetricValue"] {color:#f4f7ff;}
.hero {background:linear-gradient(115deg,#172846,#14213b 55%,#1b2944);border:1px solid #2b4166;border-radius:20px;padding:24px 28px;margin-bottom:18px;}
.hero-kicker {color:#9db9e8;font-size:.78rem;letter-spacing:.12em;font-weight:700;}
.hero h1 {color:#f4f7ff;margin:7px 0 4px;font-size:2rem;}
.hero p {color:#bdcbe0;margin:0;}
.muted {color:#9aabc4;font-size:.88rem;}
.stAlert {border-radius:12px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<div class="hero-kicker">INDIA • MARKET EDUCATION • HISTORICAL RESEARCH</div>
<h1>🇮🇳 NSE AI Market Lab</h1>
<p>Explore historical market data, understand financial concepts, and learn how to question data.</p>
</div>
""", unsafe_allow_html=True)

st.info("Educational project only. This dashboard describes historical data and financial concepts. It does not provide buy/sell recommendations, forecasts, trade setups, broker connections, or real orders. Yahoo Finance data is unofficial and may be delayed, incomplete, or unavailable.")

with st.sidebar:
    st.markdown("## 🔎 Market explorer")
    symbol_input = st.text_input("NSE/BSE symbol", value="RELIANCE.NS", help="Examples: RELIANCE.NS, TCS.NS, INFY.NS, SBIN.BO")
    period = st.selectbox("Historical period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    interval = st.selectbox("Data interval", ["1d", "1wk", "1mo"], index=0)
    load = st.button("↻ Load historical data", type="primary", use_container_width=True)
    st.divider()
    st.markdown("**Data source**")
    st.caption("Yahoo Finance (unofficial). Verify important information with exchange filings and other authoritative sources.")
    st.markdown("**Learning mode**")
    st.caption("All portfolio values are fictional points. No broker or trading account is connected.")

if "data" not in st.session_state:
    st.session_state.data = None
if "symbol" not in st.session_state:
    st.session_state.symbol = "RELIANCE.NS"

requested_symbol = symbol_input.strip().upper()
if load or st.session_state.data is None:
    if not requested_symbol:
        st.error("Enter a valid ticker symbol first.")
    else:
        try:
            with st.spinner(f"Loading historical data for {requested_symbol}…"):
                downloaded = yf.download(requested_symbol, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
                if isinstance(downloaded.columns, pd.MultiIndex):
                    downloaded.columns = downloaded.columns.get_level_values(0)
                downloaded = downloaded.dropna(how="all")
                required = {"Open", "High", "Low", "Close"}
                if downloaded.empty or not required.issubset(set(downloaded.columns)):
                    st.session_state.data = None
                    st.error("No usable historical data was returned. Check the ticker and try again later.")
                else:
                    st.session_state.data = downloaded
                    st.session_state.symbol = requested_symbol
                    st.session_state.loaded_period = period
                    st.session_state.loaded_interval = interval
        except Exception:
            st.session_state.data = None
            st.error("The data request could not be completed. Check your internet connection, ticker spelling, or try again later.")

df = st.session_state.data
if df is not None and not df.empty:
    ticker = st.session_state.symbol
    close = df["Close"].astype(float).dropna()
    if close.empty:
        st.error("The returned dataset does not contain usable closing values.")
        st.stop()
    latest = float(close.iloc[-1])
    first = float(close.iloc[0])
    period_change = ((latest / first) - 1) * 100 if first else 0.0
    period_high = float(df["High"].max())
    period_low = float(df["Low"].min())
    avg20 = float(close.tail(20).mean())
    date_start = df.index.min().strftime("%d %b %Y")
    date_end = df.index.max().strftime("%d %b %Y")

    st.subheader(f"{ticker} · Historical overview")
    st.markdown(f'<p class="muted">Showing {len(df):,} observations from {date_start} to {date_end} · Period: {st.session_state.loaded_period} · Interval: {st.session_state.loaded_interval}</p>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest available close", f"₹{latest:,.2f}")
    c2.metric("Change in selected period", f"{period_change:+.2f}%")
    c3.metric("Period high", f"₹{period_high:,.2f}")
    c4.metric("Period low", f"₹{period_low:,.2f}")

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Historical charts", "🧠 Research desk", "📚 Learning centre", "🧪 Classroom portfolio"])

    with tab1:
        st.markdown("### Price history")
        chart_type = st.radio("Chart style", ["Candlestick", "Closing line"], horizontal=True)
        fig = go.Figure()
        if chart_type == "Candlestick":
            fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Historical price"))
        else:
            fig.add_trace(go.Scatter(x=df.index, y=close, mode="lines", name="Closing price", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=close.rolling(20).mean(), mode="lines", name="20-observation average", line=dict(width=2, dash="dot")))
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=25,b=10), legend=dict(orientation="h",y=1.08), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,24,42,0)")
        st.plotly_chart(fig, use_container_width=True)
        if "Volume" in df.columns:
            st.markdown("### Trading volume history")
            vol = go.Figure(go.Bar(x=df.index, y=df["Volume"], name="Volume"))
            vol.update_layout(height=230, template="plotly_dark", margin=dict(l=10,r=10,t=15,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,24,42,0)")
            st.plotly_chart(vol, use_container_width=True)
        st.caption("The 20-observation average is a descriptive summary of past data, not a trading signal.")

    with tab2:
        st.markdown("### Multi-agent educational research desk")
        st.caption("These are transparent analysis roles using the displayed dataset—not autonomous trading agents.")
        daily = close.pct_change().dropna()
        volatility = float(daily.std() * (252 ** 0.5) * 100) if len(daily) > 1 else 0.0
        above_avg = latest >= avg20
        agents = [
            ("1 · Data-quality reviewer", f"The dataset contains {len(df):,} observations from {date_start} to {date_end}. Check missing dates, unusual values, and confirm important figures with an authoritative source."),
            ("2 · Chart explainer", f"The latest close is {'above' if above_avg else 'below'} the 20-observation average for this sample. This describes the selected history only; it does not forecast the next movement."),
            ("3 · Risk-literacy educator", f"Simple annualised historical volatility estimate: {volatility:.1f}%. Volatility measures variation in past returns; it does not tell you the outcome of a future investment."),
            ("4 · Market-context researcher", "A single company chart is only one part of the picture. Company announcements, sector conditions, broad indices, and economic events may also matter."),
            ("5 · Skeptical reviewer", "Question the first interpretation. The selected period may be unusual, adjusted prices may differ from other sources, and historical patterns may not continue.")
        ]
        for title, body in agents:
            with st.expander(title, expanded=True):
                st.write(body)
        st.warning("This research desk intentionally does not generate stock picks, entry/exit levels, targets, or stop-loss values.")

    with tab3:
        st.markdown("### Learn the language of markets")
        lessons = {
            "Candlestick": "A candlestick summarises open, high, low and close for one time interval. The body represents the open-to-close range; the wicks show the interval's extremes.",
            "Volume": "Volume counts the shares traded during an interval. It can provide context, but volume alone does not explain why a price changed.",
            "Moving average": "A moving average smooths a sequence of earlier prices. It is a descriptive summary, not a prediction.",
            "Volatility": "Volatility describes how much returns have varied. Historical volatility describes the past and cannot guarantee future outcomes.",
            "Diversification": "Diversification means spreading exposure across different assets or sectors. It can reduce concentration, but it cannot remove every kind of risk.",
            "Backtesting limitations": "A backtest applies a method to historical data. Missing data, survivorship bias, overfitting, costs, and changing conditions can make results misleading.",
            "Market index": "A market index tracks a selected group of securities using a defined method. It can help describe a segment of the market, but it is not the entire market.",
            "Corporate action": "A corporate action is an event initiated by a company that can affect its securities or shareholders, such as a split, bonus issue, or dividend."
        }
        topic = st.selectbox("Choose a concept", list(lessons))
        st.info(lessons[topic])
        st.markdown("**Quick reflection**")
        st.write("Can you explain this concept in your own words and give one example?")

    with tab4:
        st.markdown("### Classroom portfolio · virtual points only")
        st.write("A simple classroom demonstration for understanding fictional holdings and values. It is not connected to a broker and does not place orders.")
        if "virtual_points" not in st.session_state:
            st.session_state.virtual_points = 10000.0
        if "virtual_units" not in st.session_state:
            st.session_state.virtual_units = 0.0
        a, b = st.columns(2)
        a.metric("Starting virtual points", "10,000")
        b.metric("Virtual units recorded", f"{st.session_state.virtual_units:.2f}")
        st.caption("The classroom demo records no real transactions and does not use real money.")
        if st.button("Reset classroom demo"):
            st.session_state.virtual_points = 10000.0
            st.session_state.virtual_units = 0.0
            st.success("Classroom demo reset.")

    with st.expander("🗂️ Raw data preview and CSV export"):
        st.dataframe(df.tail(30), use_container_width=True)
        st.download_button("⬇️ Download displayed history as CSV", data=df.to_csv().encode("utf-8"), file_name=f"{ticker.replace('.', '_')}_history.csv", mime="text/csv")
else:
    st.markdown("### Start exploring")
    st.write("Enter an NSE or BSE symbol in the sidebar, choose a historical period, and select Load historical data.")
    st.write("Examples: RELIANCE.NS, TCS.NS, INFY.NS, SBIN.BO.")
    st.caption("If data is unavailable, check the ticker spelling or try again later.")

st.divider()
st.caption("NSE AI Market Lab · Built for learning data visualisation and financial literacy · Not investment advice.")
