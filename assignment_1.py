from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from stock import Stock

END = date.today() - timedelta(days=1)
START = date.today() - timedelta(days=365)

st.set_page_config(layout="wide", page_title="Stock Analysis", page_icon="📈")
st.title("Stock Analysis")


@st.cache_data
def load_stock(ticker, start_date, end_date, ma_window, ma_window_long=None):
    """Create (and therefore download) a Stock. Cached so widgets don't re-fetch."""
    return Stock(ticker, start=start_date, end=end_date,
                 ma_window=ma_window, ma_window_long=ma_window_long)


# --- Sidebar (shared by both tabs) ---
st.sidebar.title("Inputs")
ticker = st.sidebar.text_input("Enter stock ticker symbol", value="AAPL").strip().upper()
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start date", value=START)
end_date = col2.date_input("End date", value=END)
ma_short = st.sidebar.slider("Short moving average window (days)",
                             min_value=5, max_value=200, value=20, step=1)
ma_long = st.sidebar.slider("Long moving average window (days)",
                            min_value=5, max_value=200, value=50, step=1)

# A button only stays True for one rerun, so remember that it was clicked
if st.sidebar.button("Run Analysis", type="primary"):
    st.session_state.run = True

if start_date >= end_date:
    st.sidebar.error("Start date must be before end date.")
    st.stop()

if not st.session_state.get("run"):
    st.info("Choose your inputs in the sidebar and click **Run Analysis**.")
    st.stop()

tab1, tab2 = st.tabs(["Single Stock Analysis", "Portfolio Comparison"])

# --- Tab 1: Single Stock Analysis ---
with tab1:
    with st.spinner(f"Fetching {ticker} data..."):
        stock = load_stock(ticker, start_date, end_date, ma_short, ma_long)

    if stock.data is None:
        st.error(stock.message)
    else:
        st.success(stock.message)
        df = stock.data
        st.subheader(f"{ticker} Price Analysis")

        m1, m2, m3 = st.columns(3)
        m1.metric("Last Close", f"${df['Close'].iloc[-1]:.2f}")
        m2.metric("Cumulative Return", f"{df['return'].sum():.2%}")
        m3.metric("Trading Days", f"{len(df)}")

        # Close with both moving averages (first window-1 MA values are NaN, Plotly skips them)
        fig = px.line(df, y=["Close", "MA", "MA_long"],
                      title=f"{ticker} Close with {ma_short}- and {ma_long}-day Moving Averages",
                      labels={"value": "Price ($)", "variable": ""})
        fig.for_each_trace(lambda t: t.update(name={"MA": f"MA {ma_short}",
                                                    "MA_long": f"MA {ma_long}"}.get(t.name, t.name)))
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

        c1, c2 = st.columns(2)
        c1.plotly_chart(stock.plot_performance(), width="stretch")
        c2.plotly_chart(stock.plot_return_dist(), width="stretch")

        st.subheader("Daily Return Statistics")
        st.dataframe(df["return"].describe().to_frame("return"))

# --- Tab 2: Portfolio Comparison ---
with tab2:
    tickers_input = st.text_input("Enter ticker symbols separated by commas",
                                  value="AAPL, MSFT, GOOG")
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    returns = {}
    with st.spinner("Fetching portfolio data..."):
        for t in tickers:
            s = load_stock(t, start_date, end_date, ma_short)
            if s.data is None:
                st.error(f"{t}: {s.message}")
                continue
            returns[t] = s.data["return"]

    if returns:
        # Keep only dates every ticker traded, then rebase so each line starts at 0.0
        perf = pd.DataFrame(returns).dropna().cumsum()
        perf = perf - perf.iloc[0]

        fig = px.line(perf, title="Zero-based Cumulative Performance",
                      labels={"value": "Cumulative Return", "index": "Date",
                              "variable": "Ticker"})
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(yaxis_tickformat=".1%", hovermode="x unified")
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Starting values on {perf.index[0].date()}: "
                   + ", ".join(f"{t} = {v:.1f}" for t, v in perf.iloc[0].items()))
    else:
        st.warning("No valid tickers to compare.")
