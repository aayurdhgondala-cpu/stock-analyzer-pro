import streamlit as st
import requests
import os
from datetime import datetime, timedelta
from google import genai
from streamlit_autorefresh import st_autorefresh

ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")

DEFAULT_WATCHLIST = ["AAPL", "TSLA", "MSFT", "NVDA", "AMZN"]

st.set_page_config(
    page_title="Best of All Time — Live Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

# ──────────────────────────────────────────────────────── mobile-friendly CSS ──
st.markdown("""
<style>
/* Tighten metrics on small screens */
@media (max-width: 768px) {
    [data-testid="metric-container"] { padding: 0.4rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    [data-testid="stMetricDelta"] { font-size: 0.75rem !important; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.1rem !important; }
    h3 { font-size: 1rem !important; }
}
/* Alert banner pulse animation */
@keyframes pulse-green {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.75; }
}
@keyframes pulse-red {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.75; }
}
.alert-buy {
    animation: pulse-green 2s ease-in-out infinite;
    background: linear-gradient(90deg, #00695c, #00897b);
    border-radius: 8px;
    padding: 0.75rem 1.25rem;
    color: white;
    font-weight: 700;
    font-size: 1.1rem;
    text-align: center;
    margin-bottom: 0.75rem;
    letter-spacing: 0.03em;
}
.alert-sell {
    animation: pulse-red 2s ease-in-out infinite;
    background: linear-gradient(90deg, #b71c1c, #e53935);
    border-radius: 8px;
    padding: 0.75rem 1.25rem;
    color: white;
    font-weight: 700;
    font-size: 1.1rem;
    text-align: center;
    margin-bottom: 0.75rem;
    letter-spacing: 0.03em;
}
.alert-neutral {
    background: linear-gradient(90deg, #1a237e, #283593);
    border-radius: 8px;
    padding: 0.6rem 1.25rem;
    color: #b0bec5;
    font-size: 0.9rem;
    text-align: center;
    margin-bottom: 0.75rem;
}
.verdict-bullet {
    padding: 0.35rem 0;
    font-size: 0.95rem;
    line-height: 1.5;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────── helpers ──

@st.cache_data(ttl=60, show_spinner=False)
def fetch_global_quote(symbol: str):
    if not ALPHA_VANTAGE_KEY:
        return {}
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": ALPHA_VANTAGE_KEY},
            timeout=10,
        )
        return r.json().get("Global Quote", {})
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_sma(symbol: str, period: int = 50):
    if not ALPHA_VANTAGE_KEY:
        return None
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "SMA", "symbol": symbol, "interval": "daily",
                "time_period": period, "series_type": "close", "apikey": ALPHA_VANTAGE_KEY,
            },
            timeout=10,
        )
        analysis = r.json().get("Technical Analysis: SMA", {})
        if analysis:
            return float(analysis[sorted(analysis.keys(), reverse=True)[0]]["SMA"])
        return None
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_rsi(symbol: str):
    if not ALPHA_VANTAGE_KEY:
        return None
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "RSI", "symbol": symbol, "interval": "daily",
                "time_period": 14, "series_type": "close", "apikey": ALPHA_VANTAGE_KEY,
            },
            timeout=10,
        )
        analysis = r.json().get("Technical Analysis: RSI", {})
        if analysis:
            return float(analysis[sorted(analysis.keys(), reverse=True)[0]]["RSI"])
        return None
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_news(symbol: str):
    if not FINNHUB_KEY:
        return []
    try:
        to_date = datetime.today().strftime("%Y-%m-%d")
        from_date = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        r = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={"symbol": symbol, "from": from_date, "to": to_date, "token": FINNHUB_KEY},
            timeout=10,
        )
        data = r.json()
        return data[:10] if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def fetch_ai_sentiment(symbol: str, headlines: tuple):
    """Original single-line Bullish/Bearish score."""
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
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        text = response.text.strip()
        sentiment, reason = None, None
        for line in text.splitlines():
            if line.lower().startswith("sentiment:"):
                sentiment = line.split(":", 1)[1].strip()
            elif line.lower().startswith("reason:"):
                reason = line.split(":", 1)[1].strip()
        return sentiment, reason
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=120, show_spinner=False)
def fetch_ai_verdict(symbol: str, headlines: tuple):
    """Elite 3-bullet Bull/Bear verdict for the sidebar Intelligence Panel."""
    if not GEMINI_KEY or not headlines:
        return None, []
    try:
        client = genai.Client(api_key=GEMINI_KEY)
        headline_text = "\n".join(f"- {h}" for h in headlines[:10])
        prompt = (
            f"You are an elite Wall Street analyst. Analyze these recent news headlines for {symbol}.\n\n"
            f"Headlines:\n{headline_text}\n\n"
            f"Respond in EXACTLY this format (no extra lines):\n"
            f"Verdict: BULLISH\n"
            f"• [Factor 1 — max 12 words]\n"
            f"• [Factor 2 — max 12 words]\n"
            f"• [Factor 3 — max 12 words]\n\n"
            f"Use BULLISH or BEARISH for Verdict."
        )
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        text = response.text.strip()
        verdict, bullets = None, []
        for line in text.splitlines():
            line = line.strip()
            if line.lower().startswith("verdict:"):
                verdict = line.split(":", 1)[1].strip().upper()
            elif line.startswith("•"):
                bullets.append(line[1:].strip())
        return verdict, bullets[:3]
    except Exception:
        return None, []


def rsi_status(rsi_val: float):
    if rsi_val <= 30:
        return "buy"
    elif rsi_val >= 70:
        return "sell"
    return "neutral"


def tradingview_widget(symbol: str) -> str:
    return f"""
    <div class="tradingview-widget-container" style="height:520px;width:100%">
      <div id="tv_chart" style="height:100%;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%",
        "height": 520,
        "symbol": "{symbol}",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#1e1e2e",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tv_chart",
        "studies": [
          {{
            "id": "MASimple@tv-scriptstd",
            "inputs": {{"length": 50}},
            "override": {{"Plot.color": "#2196F3"}}
          }},
          {{
            "id": "MASimple@tv-scriptstd",
            "inputs": {{"length": 200}},
            "override": {{"Plot.color": "#FF9800"}}
          }},
          {{
            "id": "BB@tv-scriptstd",
            "inputs": {{"length": 20, "mult": 2}},
            "override": {{
              "Upper.color": "#9C27B0",
              "Lower.color": "#9C27B0",
              "Median.color": "#E91E63"
            }}
          }},
          {{
            "id": "RSI@tv-scriptstd",
            "inputs": {{"length": 14}}
          }}
        ]
      }});
      </script>
    </div>
    """


# ──────────────────────────────────────────────────────── session state init ──

if "watchlist" not in st.session_state:
    st.session_state.watchlist = list(DEFAULT_WATCHLIST)
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = "AAPL"

# ────────────────────────────────────────────────────────────────── sidebar ──

with st.sidebar:
    st.title("📋 Watchlist")
    st.caption("Tap any stock to load it")

    with st.form("add_form", clear_on_submit=True):
        new_sym = st.text_input("Symbol", placeholder="e.g. GOOGL", label_visibility="collapsed")
        if st.form_submit_button("➕ Add", use_container_width=True) and new_sym:
            sym_clean = new_sym.upper().strip()
            if sym_clean and sym_clean not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym_clean)
                st.session_state.active_ticker = sym_clean
                st.rerun()

    st.divider()

    for sym in list(st.session_state.watchlist):
        q = fetch_global_quote(sym)
        price_str, change_str, is_up = "—", "", None
        if q and q.get("05. price"):
            price_str = f"${float(q['05. price']):,.2f}"
            try:
                pct = float(q.get("10. change percent", "0%").replace("%", ""))
                is_up = pct >= 0
                change_str = f"{'▲' if is_up else '▼'} {abs(pct):.2f}%"
            except Exception:
                pass

        is_active = sym == st.session_state.active_ticker
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            label = f"→ {sym}" if is_active else sym
            if st.button(label, key=f"wl_{sym}", use_container_width=True):
                st.session_state.active_ticker = sym
                st.rerun()
        with c2:
            color = "#00c853" if is_up else "#ff5252" if is_up is False else "#90a4ae"
            st.markdown(
                f"<span style='color:{color};font-size:0.85rem'>{price_str}<br><small>{change_str}</small></span>",
                unsafe_allow_html=True,
            )
        with c3:
            if st.button("✕", key=f"del_{sym}"):
                st.session_state.watchlist.remove(sym)
                if st.session_state.active_ticker == sym:
                    st.session_state.active_ticker = (st.session_state.watchlist[0] if st.session_state.watchlist else "")
                st.rerun()

    st.divider()

    # ── AI Intelligence Panel ──────────────────────────────────────────────
    ticker_for_verdict = st.session_state.active_ticker
    st.subheader(f"🧠 AI Intel · {ticker_for_verdict}")

    verdict_news = fetch_news(ticker_for_verdict)
    if not GEMINI_KEY:
        st.caption("Add GEMINI_KEY to enable.")
    elif not verdict_news:
        st.caption("No recent news to analyze.")
    else:
        verdict_headlines = tuple(a.get("headline", "") for a in verdict_news if a.get("headline"))
        with st.spinner("Analyzing…"):
            verdict, bullets = fetch_ai_verdict(ticker_for_verdict, verdict_headlines)

        if verdict:
            if "BULLISH" in verdict:
                st.markdown("#### 🟢 BULLISH VERDICT")
            else:
                st.markdown("#### 🔴 BEARISH VERDICT")

            for b in bullets:
                st.markdown(f'<div class="verdict-bullet">• {b}</div>', unsafe_allow_html=True)
        else:
            st.caption("Could not generate verdict.")

    st.divider()
    auto_refresh = st.toggle("Auto-refresh every 60s", value=True)
    st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")

# ──────────────────────────────────────────────────── non-blocking auto-refresh ──

if auto_refresh:
    st_autorefresh(interval=60_000, key="auto_refresh_counter")

# ───────────────────────────────────────────────────────────────── main panel ──

ticker = st.session_state.active_ticker

st.title("📈 Best of All Time — Live Stock Analyzer")
st.caption("Real-time prices · AI sentiment · TradingView Pro charts · Live news")

c_sym, c_btn = st.columns([4, 1])
with c_sym:
    typed = st.text_input(
        "Symbol",
        value=ticker,
        placeholder="e.g. AAPL, TSLA, MSFT",
        label_visibility="collapsed",
    ).upper().strip()
    if typed and typed != ticker:
        st.session_state.active_ticker = typed
        if typed not in st.session_state.watchlist:
            st.session_state.watchlist.append(typed)
        st.rerun()
with c_btn:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── fetch all data ───────────────────────────────────────────────────────────
if not ticker:
    st.info("Enter a stock symbol to get started.")
    st.stop()

with st.spinner(f"Loading **{ticker}**…"):
    quote   = fetch_global_quote(ticker)
    sma50   = fetch_sma(ticker, 50)
    sma200  = fetch_sma(ticker, 200)
    rsi_val = fetch_rsi(ticker)
    news    = fetch_news(ticker)

price      = float(quote.get("05. price", 0))    if quote.get("05. price")    else None
change     = float(quote.get("09. change", 0))   if quote.get("09. change")   else None
change_pct = quote.get("10. change percent", "0%").replace("%", "")
volume     = quote.get("06. volume", "N/A")
high       = quote.get("03. high",  "N/A")
low        = quote.get("04. low",   "N/A")
prev_close = quote.get("08. previous close", "N/A")

# ── ELITE FEATURE 3 — Visual RSI Alert Banner ────────────────────────────────
if rsi_val is not None:
    status = rsi_status(rsi_val)
    if status == "buy":
        st.markdown(
            f'<div class="alert-buy">🟢 OVERSOLD — POTENTIAL BUY SIGNAL &nbsp;|&nbsp; RSI: {rsi_val:.1f} &nbsp;|&nbsp; {ticker}</div>',
            unsafe_allow_html=True,
        )
    elif status == "sell":
        st.markdown(
            f'<div class="alert-sell">🔴 OVERBOUGHT — POTENTIAL SELL SIGNAL &nbsp;|&nbsp; RSI: {rsi_val:.1f} &nbsp;|&nbsp; {ticker}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="alert-neutral">RSI: {rsi_val:.1f} — Neutral zone (30–70)</div>',
            unsafe_allow_html=True,
        )

# ── Metrics — 2 rows of 3 (mobile-friendly) ──────────────────────────────────
r1c1, r1c2, r1c3 = st.columns(3)
r2c1, r2c2, r2c3 = st.columns(3)

with r1c1:
    if price is not None:
        delta = f"{change:+.2f} ({change_pct}%)" if change is not None else None
        st.metric("💵 Live Price", f"${price:,.2f}", delta=delta)
    else:
        st.metric("💵 Live Price", "—")

with r1c2:
    if sma50 is not None:
        tag = "▲ Above" if price and price > sma50 else "▼ Below"
        st.metric("📊 50-Day MA", f"${sma50:,.2f}", delta=f"{tag} SMA")
    else:
        st.metric("📊 50-Day MA", "—")

with r1c3:
    if sma200 is not None:
        tag200 = "▲ Above" if price and price > sma200 else "▼ Below"
        st.metric("📈 200-Day MA", f"${sma200:,.2f}", delta=f"{tag200} SMA")
    else:
        st.metric("📈 200-Day MA", "—")

with r2c1:
    if rsi_val is not None:
        lbl = "🔴 Overbought" if rsi_val >= 70 else "🟢 Oversold" if rsi_val <= 30 else "🟡 Neutral"
        st.metric("⚡ RSI (14)", f"{rsi_val:.1f}", delta=lbl)
    else:
        st.metric("⚡ RSI (14)", "—")

with r2c2:
    try:
        st.metric("📈 Day High", f"${float(high):,.2f}")
    except Exception:
        st.metric("📈 Day High", "—")

with r2c3:
    try:
        st.metric("📉 Day Low", f"${float(low):,.2f}")
    except Exception:
        st.metric("📉 Day Low", "—")

st.divider()

# ── ELITE FEATURE 1 — TradingView with 200-Day MA + Bollinger Bands ──────────
st.subheader(f"📉 {ticker} — Advanced Chart | 50-MA · 200-MA · Bollinger Bands · RSI")
st.components.v1.html(tradingview_widget(ticker), height=540, scrolling=False)

st.divider()

# ── AI Brain + News ───────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    st.subheader("🤖 AI Brain — Sentiment")
    if not GEMINI_KEY:
        st.info("Add GEMINI_KEY to enable AI analysis.")
    elif not news:
        st.info("No recent news found to analyze.")
    else:
        headlines = tuple(a.get("headline", "") for a in news if a.get("headline"))
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
    try:
        st.write(f"**Prev Close:** ${float(prev_close):,.2f}" if prev_close != "N/A" else "**Prev Close:** —")
    except Exception:
        st.write("**Prev Close:** —")
    try:
        st.write(f"**Volume:** {int(volume):,}" if volume != "N/A" else "**Volume:** —")
    except Exception:
        st.write("**Volume:** —")
    st.write(f"**Symbol:** {quote.get('01. symbol', ticker)}")
    st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

with right_col:
    st.subheader("📰 Live News Feed")
    if not FINNHUB_KEY:
        st.info("Add FINNHUB_KEY to enable news.")
    elif not news:
        st.info("No recent news articles found.")
    else:
        for article in news:
            headline = article.get("headline", "No headline")
            source   = article.get("source", "Unknown")
            url      = article.get("url", "#")
            summary  = article.get("summary", "")
            ts       = article.get("datetime", 0)
            try:
                pub_time = datetime.fromtimestamp(ts).strftime("%b %d, %H:%M")
            except Exception:
                pub_time = "—"

            with st.expander(f"{headline[:85]}{'…' if len(headline) > 85 else ''}"):
                st.caption(f"🕐 {pub_time} · {source}")
                if summary:
                    st.write(summary[:280] + ("…" if len(summary) > 280 else ""))
                st.markdown(f"[Read full article ↗]({url})")
