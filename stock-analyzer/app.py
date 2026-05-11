import streamlit as st
import requests
import pandas as pd
import os
import time
from datetime import datetime, timedelta
from google import genai

ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")

st.set_page_config(
    page_title="Best of All Time — Live Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("📈 Best of All Time — Live Stock Analyzer")
st.caption("Real-time prices · AI sentiment · Live news · TradingView charts")

# --- Ticker input ---
col_ticker, col_refresh, col_auto = st.columns([2, 1, 2])
with col_ticker:
    ticker = st.text_input("Stock Symbol", value="AAPL", placeholder="e.g. AAPL, TSLA, MSFT").upper().strip()
with col_refresh:
    st.write("")
    manual_refresh = st.button("🔄 Refresh Now", use_container_width=True)
with col_auto:
    auto_refresh = st.toggle("Auto-refresh every 30s", value=True)

st.divider()

# ------------------------------------------------------------------ helpers --

@st.cache_data(ttl=30, show_spinner=False)
def fetch_global_quote(symbol: str):
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
    )
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get("Global Quote", {})
        return data
    except Exception:
        return {}


@st.cache_data(ttl=30, show_spinner=False)
def fetch_sma(symbol: str):
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=SMA&symbol={symbol}&interval=daily"
        f"&time_period=50&series_type=close&apikey={ALPHA_VANTAGE_KEY}"
    )
    try:
        r = requests.get(url, timeout=10)
        analysis = r.json().get("Technical Analysis: SMA", {})
        if analysis:
            latest_date = sorted(analysis.keys(), reverse=True)[0]
            return float(analysis[latest_date]["SMA"]), latest_date
        return None, None
    except Exception:
        return None, None


@st.cache_data(ttl=30, show_spinner=False)
def fetch_rsi(symbol: str):
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=RSI&symbol={symbol}&interval=daily"
        f"&time_period=14&series_type=close&apikey={ALPHA_VANTAGE_KEY}"
    )
    try:
        r = requests.get(url, timeout=10)
        analysis = r.json().get("Technical Analysis: RSI", {})
        if analysis:
            latest_date = sorted(analysis.keys(), reverse=True)[0]
            return float(analysis[latest_date]["RSI"]), latest_date
        return None, None
    except Exception:
        return None, None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_news(symbol: str):
    to_date = datetime.today().strftime("%Y-%m-%d")
    from_date = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    url = (
        f"https://finnhub.io/api/v1/company-news"
        f"?symbol={symbol}&from={from_date}&to={to_date}&token={FINNHUB_KEY}"
    )
    try:
        r = requests.get(url, timeout=10)
        articles = r.json()
        if isinstance(articles, list):
            return articles[:10]
        return []
    except Exception:
        return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_ai_sentiment(symbol: str, headlines: list[str]):
    if not GEMINI_KEY or not headlines:
        return None, None
    try:
        client = genai.Client(api_key=GEMINI_KEY)
        headline_text = "\n".join(f"- {h}" for h in headlines[:8])
        prompt = (
            f"You are a financial analyst. Based on these recent news headlines for {symbol}, "
            f"give a single sentiment score as either 'Bullish' or 'Bearish', "
            f"followed by one concise sentence (max 25 words) explaining why.\n\n"
            f"Headlines:\n{headline_text}\n\n"
            f"Reply in exactly this format:\nSentiment: [Bullish or Bearish]\nReason: [one sentence]"
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        text = response.text.strip()
        sentiment = None
        reason = None
        for line in text.splitlines():
            if line.lower().startswith("sentiment:"):
                sentiment = line.split(":", 1)[1].strip()
            elif line.lower().startswith("reason:"):
                reason = line.split(":", 1)[1].strip()
        return sentiment, reason
    except Exception as e:
        return None, str(e)


def rsi_label(rsi_val: float) -> str:
    if rsi_val >= 70:
        return "🔴 Overbought"
    elif rsi_val <= 30:
        return "🟢 Oversold"
    else:
        return "🟡 Neutral"


def tradingview_widget(symbol: str) -> str:
    return f"""
    <div class="tradingview-widget-container" style="height:500px;width:100%">
      <div id="tradingview_chart" style="height:100%;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%",
        "height": 500,
        "symbol": "{symbol}",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#1e1e2e",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart",
        "studies": [
          "MASimple@tv-scriptstd",
          "RSI@tv-scriptstd"
        ]
      }});
      </script>
    </div>
    """


# ------------------------------------------------------------------ main UI --

if not ticker:
    st.info("Enter a stock symbol above to get started.")
    st.stop()

missing_keys = []
if not ALPHA_VANTAGE_KEY:
    missing_keys.append("ALPHA_VANTAGE_KEY")
if not FINNHUB_KEY:
    missing_keys.append("FINNHUB_KEY")
if not GEMINI_KEY:
    missing_keys.append("GEMINI_KEY")

if missing_keys:
    st.warning(
        f"⚠️ Missing API keys: **{', '.join(missing_keys)}**. "
        "Add them in the Secrets tool (🔒) on the left sidebar, then refresh."
    )

# Fetch all data
with st.spinner(f"Loading live data for **{ticker}**…"):
    quote = fetch_global_quote(ticker)
    sma_val, sma_date = fetch_sma(ticker)
    rsi_val, rsi_date = fetch_rsi(ticker)
    news = fetch_news(ticker)

# --- Key metrics row ---
price = float(quote.get("05. price", 0)) if quote.get("05. price") else None
change = float(quote.get("09. change", 0)) if quote.get("09. change") else None
change_pct = quote.get("10. change percent", "0%").replace("%", "")
volume = quote.get("06. volume", "N/A")
high = quote.get("03. high", "N/A")
low = quote.get("04. low", "N/A")
prev_close = quote.get("08. previous close", "N/A")

m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    if price is not None:
        delta_str = f"{change:+.2f} ({change_pct}%)" if change is not None else None
        st.metric("💵 Live Price", f"${price:,.2f}", delta=delta_str)
    else:
        st.metric("💵 Live Price", "—")

with m2:
    if sma_val is not None:
        above_below = "▲ Above SMA" if price and price > sma_val else "▼ Below SMA"
        st.metric("📊 50-Day MA", f"${sma_val:,.2f}", delta=above_below)
    else:
        st.metric("📊 50-Day MA", "—")

with m3:
    if rsi_val is not None:
        st.metric("⚡ RSI (14)", f"{rsi_val:.1f}", delta=rsi_label(rsi_val))
    else:
        st.metric("⚡ RSI (14)", "—")

with m4:
    st.metric("📈 Day High", f"${float(high):,.2f}" if high != "N/A" else "—")

with m5:
    st.metric("📉 Day Low", f"${float(low):,.2f}" if low != "N/A" else "—")

st.divider()

# --- TradingView Chart ---
st.subheader(f"📉 {ticker} Advanced Chart (Dark Mode)")
st.components.v1.html(tradingview_widget(ticker), height=520, scrolling=False)

st.divider()

# --- AI Brain + News side by side ---
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    st.subheader("🤖 AI Brain — Sentiment Analysis")
    if not GEMINI_KEY:
        st.info("Add your GEMINI_KEY secret to enable AI analysis.")
    elif not news:
        st.info("No recent news found to analyze.")
    else:
        headlines = [a.get("headline", "") for a in news if a.get("headline")]
        with st.spinner("Asking Gemini…"):
            sentiment, reason = fetch_ai_sentiment(ticker, headlines)

        if sentiment:
            if "bullish" in sentiment.lower():
                st.success(f"### 🟢 {sentiment}")
            elif "bearish" in sentiment.lower():
                st.error(f"### 🔴 {sentiment}")
            else:
                st.info(f"### ⚪ {sentiment}")
            if reason:
                st.write(f"**Reason:** {reason}")
        else:
            st.warning(f"Could not parse AI response. {reason or ''}")

    st.divider()
    st.subheader("📋 Quick Stats")
    stats = {
        "Previous Close": f"${float(prev_close):,.2f}" if prev_close != "N/A" else "—",
        "Volume": f"{int(volume):,}" if volume != "N/A" else "—",
        "Symbol": quote.get("01. symbol", ticker),
    }
    for k, v in stats.items():
        st.write(f"**{k}:** {v}")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

with right_col:
    st.subheader("📰 Live News Feed")
    if not FINNHUB_KEY:
        st.info("Add your FINNHUB_KEY secret to enable news.")
    elif not news:
        st.info("No recent news articles found.")
    else:
        for article in news:
            headline = article.get("headline", "No headline")
            source = article.get("source", "Unknown")
            url = article.get("url", "#")
            ts = article.get("datetime", 0)
            try:
                pub_time = datetime.fromtimestamp(ts).strftime("%b %d, %H:%M")
            except Exception:
                pub_time = "—"
            summary = article.get("summary", "")

            with st.expander(f"**{headline[:90]}{'…' if len(headline) > 90 else ''}**"):
                st.caption(f"🕐 {pub_time} · {source}")
                if summary:
                    st.write(summary[:300] + ("…" if len(summary) > 300 else ""))
                st.markdown(f"[Read full article ↗]({url})")

# --- Auto-refresh ---
if auto_refresh:
    time.sleep(30)
    st.rerun()
