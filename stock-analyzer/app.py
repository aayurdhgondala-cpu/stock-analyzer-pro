import streamlit as st
import os


# --- TRADING LOGIC FUNCTIONS ---
def buy_stock(ticker, stock_price):
    if st.session_state.balance >= stock_price:
        st.session_state.balance -= stock_price
        st.session_state.portfolio[ticker] = (
            st.session_state.portfolio.get(ticker, 0) + 1
        )
        st.toast(f"✅ Bought 1 share of {ticker}!", icon="💰")
    else:
        st.error("❌ Insufficient Funds!")


def sell_stock(ticker, stock_price):
    if st.session_state.portfolio.get(ticker, 0) > 0:
        st.session_state.balance += stock_price
        st.session_state.portfolio[ticker] -= 1
        st.toast(f"🚀 Sold 1 share of {ticker}!", icon="📈")
    else:
        st.error("❌ You don't own this stock!")


def buy_stock(ticker, price):
    if st.session_state.balance >= price:
        st.session_state.balance -= price
        st.session_state.portfolio[ticker] = (
            st.session_state.portfolio.get(ticker, 0) + 1
        )
        st.toast(f"✅ Bought 1 share of {ticker}!", icon="💰")
    else:
        st.error("❌ Insufficient Funds!")


def sell_stock(ticker, price):
    if st.session_state.portfolio.get(ticker, 0) > 0:
        st.session_state.balance += price
        st.session_state.portfolio[ticker] -= 1
        st.toast(f"🚀 Sold 1 share of {ticker}!", icon="📈")
    else:
        st.error("❌ You don't own this stock!")


# Force Streamlit to stay alive on the cloud port
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
import requests
import os


def buy_stock(ticker, price):
    if st.session_state.balance >= price:
        st.session_state.balance -= price
        st.session_state.portfolio[ticker] = (
            st.session_state.portfolio.get(ticker, 0) + 1
        )
        st.toast(f"✅ Bought 1 share of {ticker}!", icon="💰")
    else:
        st.error("❌ Insufficient Funds!")


def sell_stock(ticker, price):
    if st.session_state.portfolio.get(ticker, 0) > 0:
        st.session_state.balance += price
        st.session_state.portfolio[ticker] -= 1
        st.toast(f"🚀 Sold 1 share of {ticker}!", icon="📈")
    else:
        st.error("❌ You don't own this stock!")


# Add this at the beginning of your script logic
current_ticker = "AAPL"
price = 0.0
rsi_val = None
sma50 = None
from streamlit_autorefresh import st_autorefresh

# Refresh the app every 30 seconds
count = st_autorefresh(interval=30000, limit=100, key="fizzbuzzcounter")
from datetime import datetime, timedelta
from google import genai

# ── CONFIG & KEYS ────────────────────────────────────────────────────────────
ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")

DEFAULT_WATCHLIST = ["AAPL", "TSLA", "MSFT", "NVDA", "AMZN"]


# ── STEP 3: THE AI BRAIN — DECISION ENGINE ───────────────────────────────────
def get_ai_verdict(ticker, price, rsi, sma):
    if not price or not rsi or not sma:
        return "HOLD", "Analyzing technical data..."
    score = 0
    if rsi < 35:
        score += 2
    elif rsi > 65:
        score -= 2
    if price > sma:
        score += 1
    else:
        score -= 1

    if score >= 2:
        return "STRONG BUY", f"{ticker} is oversold and trending high."
    elif score <= -2:
        return "STRONG SELL", f"{ticker} is overbought and breaking trend."
    elif score == 1:
        return "ACCUMULATE", f"Sentiment is positive for {ticker}."
    else:
        return "WAIT", "Market signals are currently mixed."


st.set_page_config(
    page_title="Best of All Time — Live Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

# ── STEP 2: 30s DATA SYNC ─────────────────────────────────────────────────────
REFRESH_INTERVAL = 30 * 1000

# ── ELITE CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
    @media (max-width: 768px) {
        [data-testid="metric-container"] { padding: 0.4rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
        h1 { font-size: 1.4rem !important; }
    }
    .alert-buy { animation: pulse 2s infinite; background: linear-gradient(90deg, #00695c, #00897b); border-radius: 8px; padding: 12px; color: white; text-align: center; font-weight: bold; }
    .alert-sell { animation: pulse 2s infinite; background: linear-gradient(90deg, #b71c1c, #e53935); border-radius: 8px; padding: 12px; color: white; text-align: center; font-weight: bold; }
    @keyframes pulse { 0% {opacity: 1;} 50% {opacity: 0.8;} 100% {opacity: 1;} }
</style>
""",
    unsafe_allow_html=True,
)

# ── DATA FETCHING (OPTIMIZED) ────────────────────────────────────────────────


@st.cache_data(ttl=25, show_spinner=False)
def fetch_global_quote(symbol: str):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
        return requests.get(url, timeout=10).json().get("Global Quote", {})
    except:
        return {}


@st.cache_data(ttl=3600)
def fetch_sma(symbol: str, period: int = 50):
    try:
        url = f"https://www.alphavantage.co/query?function=SMA&symbol={symbol}&interval=daily&time_period={period}&series_type=close&apikey={ALPHA_VANTAGE_KEY}"
        analysis = requests.get(url).json().get("Technical Analysis: SMA", {})
        return (
            float(analysis[sorted(analysis.keys(), reverse=True)[0]]["SMA"])
            if analysis
            else None
        )
    except:
        return None


@st.cache_data(ttl=300)
def fetch_rsi(symbol: str):
    try:
        url = f"https://www.alphavantage.co/query?function=RSI&symbol={symbol}&interval=daily&time_period=14&series_type=close&apikey={ALPHA_VANTAGE_KEY}"
        analysis = requests.get(url).json().get("Technical Analysis: RSI", {})
        return (
            float(analysis[sorted(analysis.keys(), reverse=True)[0]]["RSI"])
            if analysis
            else None
        )
    except:
        return None


@st.cache_data(ttl=120)
def fetch_news(symbol: str):
    try:
        to_date = datetime.today().strftime("%Y-%m-%d")
        from_date = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={from_date}&to={to_date}&token={FINNHUB_KEY}"
        return requests.get(url).json()[:10]
    except:
        return []


# ── TRADINGVIEW WIDGET ───────────────────────────────────────────────────────
def tradingview_widget(symbol: str):
    return f"""
    <div class="tradingview-widget-container" style="height:500px;">
      <div id="tv_chart" style="height:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{"width": "100%", "height": 500, "symbol": "{symbol}", "interval": "D", "theme": "dark", "style": "1", "container_id": "tv_chart", "studies": ["MASimple@tv-scriptstd", "RSI@tv-scriptstd"]}});
      </script>
    </div>
    """


# ── SESSION STATE ────────────────────────────────────────────────────────────
if "balance" not in st.session_state:
    st.session_state.balance = 10000.0  # Starting with $10,000 virtual cash
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}  # To track owned stocks { "AAPL": 10 }
if "watchlist" not in st.session_state:
    st.session_state.watchlist = list(DEFAULT_WATCHLIST)
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = "AAPL"


# ── SIDEBAR ──────────────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.subheader("💰 Paper Trading")
st.sidebar.metric("Wallet Balance", f"${st.session_state.balance:,.2f}")
with st.sidebar:
    st.title("📋 Watchlist")
    auto_refresh = st.toggle("Live 30s Sync", value=True)
    if auto_refresh:
        st_autorefresh(interval=REFRESH_INTERVAL, key="datarefresh")

    st.divider()
    for sym in st.session_state.watchlist:
        c1, c2 = st.columns([3, 1])
        if c1.button(f"{sym}", key=f"btn_{sym}", use_container_width=True):
            st.session_state.active_ticker = sym
            st.rerun()
        if c2.button("✕", key=f"del_{sym}"):
            st.session_state.watchlist.remove(sym)
            st.rerun()

# ── MAIN PANEL ───────────────────────────────────────────────────────────────
ticker = st.session_state.active_ticker
st.title(f"📈 {ticker} Analyzer Pro")

with st.spinner("Fetching Live Market Data..."):
    quote = fetch_global_quote(ticker)
    rsi_val = fetch_rsi(ticker)

    news = fetch_news(ticker)


# (Keep your 'if quote:' line right here and continue as normal)

if quote:
    price = float(quote.get("05. price", 0))

    # --- FEATURE 4: VOLATILITY ALERT ---
    raw_change = quote.get("10. change percent", "0")
    change_pct = float(raw_change.strip("%"))

    if abs(change_pct) > 1.5:
        st.error(f"🚨 **VOLATILITY ALERT:** Movement is {change_pct}% today!")
        st.toast("High Market Risk!", icon="⚠️")

    # Keep your existing RSI Alert Banners below
    if rsi_val:
        # ... your existing code ...
        # Alert Banners
        if rsi_val:
            if rsi_val < 30:
                st.markdown(
                    '<div class="alert-buy">🟢 OVERSOLD: POTENTIAL BUY</div>',
                    unsafe_allow_html=True,
                )
            if rsi_val > 70:
                st.markdown(
                    '<div class="alert-sell">🔴 OVERBOUGHT: POTENTIAL SELL</div>',
                    unsafe_allow_html=True,
                )
    # --- FEATURE 4: VOLATILITY & RISK ALERTS ---
    if quote:
        # Get the daily change percentage from the API data
        change_pct_str = quote.get("10. change percent", "0").strip("%")
        change_pct = float(change_pct_str)

        # 1. Volatility Alert (for big market crashes like yesterday)
        if abs(change_pct) > 1.5:
            st.error(
                f"🚨 **CRITICAL VOLATILITY:** {st.session_state.active_ticker} is moving {change_pct}% today!"
            )
            st.toast("High Risk: Market Volatility Spike!", icon="⚠️")

        # 2. RSI Alerts (Overbought/Oversold logic)
        if rsi_val and rsi_val > 70:
            st.warning(
                f"⚠️ **OVERBOUGHT:** RSI is {rsi_val:.2f}. Potential reversal ahead."
            )
        elif rsi_val and rsi_val < 30:
            st.success(
                f"🟢 **OVERSOLD:** RSI is {rsi_val:.2f}. Potential buying opportunity."
            )
    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Live Price", f"${price:,.2f}", delta=quote.get("10. change percent"))
    m2.metric("RSI (14)", f"{rsi_val:.1f}" if rsi_val else "—")
    m3.metric("50-Day SMA", f"${sma50:,.2f}" if sma50 else "—")

st.divider()
st.subheader("Advanced Chart")
st.components.v1.html(tradingview_widget(ticker), height=520)

st.divider()
st.subheader("📰 Market Intel")
for n in news:
    with st.expander(n.get("headline", "News")):
        st.write(n.get("summary"))
        st.markdown(f"[Source: {n.get('source')}]({n.get('url')})")
        # ── DISPLAY THE AI VERDICT ───────────────────────────────────────────────────
st.divider()
st.subheader("🧠 AI Brain — Decision Center")
# This calls the "Brain" function we just added
# Use the session_state ticker instead of a generic 'ticker' variable
current_ticker = st.session_state.active_ticker
verdict, logic_reason = get_ai_verdict(current_ticker, price, rsi_val, sma50)

v_col1, v_col2 = st.columns([1, 2])
with v_col1:
    if "BUY" in verdict:
        st.success(f"### {verdict}")
    elif "SELL" in verdict:
        st.error(f"### {verdict}")
    else:
        st.warning(f"### {verdict}")
with v_col2:
    st.info(f"**AI Logic:** {logic_reason}")
st.write("---")
st.subheader("🚀 Execute Trade (Paper Trading)")
t_col1, t_col2 = st.columns(2)

# Using 'on_click' makes the change permanent
t_col1.button(
    f"BUY {current_ticker}",
    on_click=buy_stock,
    args=(current_ticker, price),
    use_container_width=True,
)

t_col2.button(
    f"SELL {current_ticker}",
    on_click=sell_stock,
    args=(current_ticker, price),
    use_container_width=True,
)
