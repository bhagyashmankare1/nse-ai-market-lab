import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(page_title="NSE AI Market Lab", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; max-width: 1450px;}
[data-testid="stMetric"] {background: rgba(120,120,120,.08); padding: 14px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.title("🇮🇳 NSE AI Market Lab")
st.caption("A free-first market education and research dashboard • Local on your computer")

st.info(
    "Learning project only. This app explains historical market data and financial concepts. "
    "It does not provide buy/sell recommendations, predictions, broker connections, or real orders. "
    "Market data may be delayed, incomplete, or unavailable."
)

with st.sidebar:
    st.header("Market explorer")
    symbol = st.text_input("NSE/BSE symbol", value="RELIANCE.NS",
                           help="Examples: TCS.NS, INFY.NS, RELIANCE.NS, SBIN.BO")
    period = st.selectbox("History", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    interval = st.selectbox("Chart interval", ["1d", "1wk", "1mo"], index=0)
    st.caption("Yahoo Finance data is unofficial and may be delayed. Use it for learning only.")
    load = st.button("Load historical data", type="primary", use_container_width=True)

if "data" not in st.session_state:
    st.session_state.data = None
if load or st.session_state.data is None:
    try:
        with st.spinner("Fetching historical data…"):
            df = yf.download(symbol.strip().upper(), period=period, interval=interval,
                             auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna()
            if df.empty:
                st.session_state.data = None
                st.error("No data returned. Check the symbol and try again.")
            else:
                st.session_state.data = df
                st.session_state.symbol = symbol.strip().upper()
    except Exception as e:
        st.session_state.data = None
        st.error(f"Data request failed: {e}")

df = st.session_state.data
if df is not None and not df.empty:
    ticker = st.session_state.get("symbol", symbol)
    close = df["Close"].astype(float)
    latest = float(close.iloc[-1])
    first = float(close.iloc[0])
    change = ((latest / first) - 1) * 100 if first else 0
    avg20 = float(close.tail(20).mean()) if len(close) >= 20 else float(close.mean())
    high = float(df["High"].max())
    low = float(df["Low"].min())

    st.subheader(f"{ticker} · Historical overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest available close", f"₹{latest:,.2f}")
    c2.metric("Change in selected period", f"{change:+.2f}%")
    c3.metric("Period high", f"₹{high:,.2f}")
    c4.metric("Period low", f"₹{low:,.2f}")

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Chart", "🧠 Research agents", "📚 Learn", "🧪 Classroom portfolio"])

    with tab1:
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name="Historical price"
        )])
        fig.add_trace(go.Scatter(x=df.index, y=close.rolling(20).mean(),
                                 mode="lines", name="20-period average"))
        fig.update_layout(height=520, xaxis_rangeslider_visible=False,
                          margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
        if "Volume" in df:
            vol = go.Figure(go.Bar(x=df.index, y=df["Volume"], name="Volume"))
            vol.update_layout(height=220, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(vol, use_container_width=True)
        st.caption("The average line is a descriptive chart overlay, not a trading signal.")

    with tab2:
        st.subheader("Multi-agent research desk")
        st.caption("These are transparent educational analysis roles, not autonomous trading agents.")
        daily = close.pct_change().dropna()
        volatility = float(daily.std() * (252 ** 0.5) * 100) if len(daily) > 1 else 0
        above_avg = latest >= avg20
        agents = [
            ("1 · Data-quality agent", f"Loaded {len(df)} observations. Date range: {df.index.min().date()} to {df.index.max().date()}. Check missing dates and confirm data with an authoritative source before drawing conclusions."),
            ("2 · Chart-explainer agent", f"The latest close is {'above' if above_avg else 'below'} the selected-period 20-observation average. This describes the sample; it does not indicate what price will do next."),
            ("3 · Risk-literacy agent", f"Annualised historical volatility estimate: {volatility:.1f}% (simple estimate from available returns). Volatility measures variation, not the chance of profit or loss on a particular day."),
            ("4 · Market-context agent", "A single stock chart does not explain the whole market. Compare it with its sector, a broad index, company announcements, and wider economic conditions."),
            ("5 · Skeptical-review agent", "Challenge the first interpretation: the selected period may be unusual, data may be adjusted, and historical patterns can disappear. Avoid treating a chart pattern as a forecast.")
        ]
        for title, body in agents:
            with st.expander(title, expanded=True):
                st.write(body)
        st.warning("No agent creates an entry, exit, target, stop-loss, or stock recommendation.")

    with tab3:
        st.subheader("Learn the language of markets")
        lessons = {
            "Candlestick": "A candle summarises open, high, low and close for one time interval. The body shows the open-to-close range; the wicks show the extremes.",
            "Volume": "Volume counts shares traded during an interval. High volume can accompany important news, but volume alone does not tell you whether a move is sustainable.",
            "Moving average": "A moving average smooths earlier prices. It is a summary of past observations, not a prediction.",
            "Volatility": "Volatility describes how widely returns have varied. Higher historical volatility means a less steady past path, not a guaranteed future outcome.",
            "Diversification": "Diversification means spreading exposure across different assets or sectors. It can reduce concentration, but it cannot remove all risk.",
            "Backtesting limitations": "A backtest applies rules to past data. Results can be distorted by missing data, survivorship bias, overfitting, transaction costs and changing market conditions."
        }
        topic = st.selectbox("Choose a concept", list(lessons))
        st.write(lessons[topic])
        st.caption("Try explaining the concept in your own words, then compare it with the explanation above.")

    with tab4:
        st.subheader("Classroom portfolio — virtual points only")
        st.write("Use fictional points to learn how portfolio values change. This is not connected to a broker and does not place orders.")
        if "virtual_points" not in st.session_state:
            st.session_state.virtual_points = 10000.0
        if "units" not in st.session_state:
            st.session_state.units = 0.0
        a, b = st.columns(2)
        a.metric("Starting virtual points", "10,000")
        b.metric("Virtual units recorded", f"{st.session_state.units:.2f}")
        st.caption("For this starter version, the classroom portfolio is a concept demo. It does not execute stock transactions.")
        if st.button("Reset classroom demo"):
            st.session_state.virtual_points = 10000.0
            st.session_state.units = 0.0
            st.success("Classroom demo reset.")

    with st.expander("Raw data preview"):
        st.dataframe(df.tail(30), use_container_width=True)
        st.download_button("Download displayed data as CSV",
                           df.to_csv().encode("utf-8"),
                           file_name=f"{ticker.replace('.', '_')}_history.csv",
                           mime="text/csv")
else:
    st.markdown("### Start exploring")
    st.write("Enter an NSE or BSE symbol in the sidebar and select **Load historical data**.")
    st.write("Examples: `RELIANCE.NS`, `TCS.NS`, `INFY.NS`, `SBIN.BO`.")
    st.write("If market data is unavailable, try again later or check the ticker spelling.")

st.divider()
st.caption("Built for learning Python, data visualisation and financial literacy. Not investment advice.")
