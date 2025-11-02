
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="BTC Bot — Carry + Risk", layout="wide", page_icon="💠")

# -------- helpers --------
def random_walk(n=800, start=60000.0, vol=60.0, seed=42):
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, vol, size=n)
    return start + steps.cumsum()
def atr_like(series, period=14):
    diffs = np.abs(np.diff(series, prepend=series[0]))
    return np.convolve(diffs, np.ones(period)/period, mode='same')
def size_by_atr(equity, risk_pct, atr_usd, atr_multiple, price, max_lev):
    stop_usd = atr_usd * atr_multiple
    risk_usd = equity * risk_pct
    if stop_usd <= 0 or price <= 0: return 0.0, risk_usd, stop_usd
    size_raw = risk_usd / stop_usd
    max_notional = equity * max_lev
    size_cap = max_notional / price
    return min(size_raw, size_cap), risk_usd, stop_usd
def net_daily_pct(funding_daily, borrow_daily, maker_fee, taker_fee, slippage_pct):
    return funding_daily - borrow_daily - maker_fee - taker_fee - slippage_pct

st.title("בוט ביטקוין — Funding Carry + ניהול סיכונים (Cloud Ready)")
st.caption("דשבורד קל לפריסה ל־Streamlit Cloud / HF Spaces. סף כניסה ל-Carry, ATR sizing וגרפים.")

with st.sidebar:
    st.subheader("הגדרות נתונים / Data")
    seed = st.number_input("Random Seed", 0, 10000, 42, step=1)
    npoints = st.slider("Data Points", 300, 2000, 800, 50)

    st.subheader("ניהול סיכונים / Risk")
    equity = st.number_input("Equity ($)", 1000, 1_000_000, 10000, 100)
    risk_pct = st.number_input("Risk per Trade %", 0.0005, 0.02, 0.003, 0.0005, format="%.4f")
    max_lev = st.slider("Max Gross Leverage", 1.0, 5.0, 2.0, 0.1)
    atr_period = st.slider("ATR Period", 5, 50, 14, 1)
    atr_mult = st.slider("Stop Multiple (ATR)", 0.5, 5.0, 1.5, 0.1)

    st.subheader("עלויות & Carry / Costs & Carry")
    maker_fee = st.number_input("Maker Fee %", 0.0, 0.01, 0.0002, 0.0001, format="%.5f")
    taker_fee = st.number_input("Taker Fee %", 0.0, 0.01, 0.0005, 0.0001, format="%.5f")
    slippage_bps = st.number_input("Slippage (bps)", 0.0, 20.0, 1.0, 0.1, format="%.1f")
    funding_annual = st.number_input("Funding Annualized %", 0.0, 0.5, 0.10, 0.01, format="%.2f")
    borrow_daily = st.number_input("Borrow Daily %", 0.0, 0.01, 0.0001, 0.0001, format="%.4f")
    min_net_daily_pct = st.number_input("Min Net Daily % (threshold)", 0.0, 0.01, 0.0005, 0.0001, format="%.4f")

# data & ATR
prices = random_walk(n=npoints, start=60000.0, vol=60.0, seed=seed)
price = float(prices[-1])
atr_vals = atr_like(prices, period=atr_period)
atr_now = float(atr_vals[-1])
size_btc, risk_usd, stop_usd = size_by_atr(equity, risk_pct, atr_now, atr_mult, price, max_lev)
loss_lock_usd = equity * 0.02

c1, c2, c3, c4 = st.columns(4)
c1.metric("BTC Price", f"{price:,.2f}")
c2.metric("ATR (USD)", f"{atr_now:,.2f}")
c3.metric("Size (BTC)", f"{size_btc:,.4f}")
c4.metric("Daily Loss Lock ($)", f"{loss_lock_usd:,.2f}")

fig = go.Figure()
fig.add_trace(go.Scatter(y=prices.tolist(), mode="lines", name="Price"))
fig.add_trace(go.Scatter(y=atr_vals.tolist(), mode="lines", name=f"ATR({atr_period})", yaxis="y2"))
fig.update_layout(template="plotly_dark", xaxis_title="Step", yaxis_title="Price",
                  yaxis2=dict(title="ATR", overlaying="y", side="right"), height=420)
st.plotly_chart(fig, use_container_width=True)

# Carry logic (paper)
funding_daily = funding_annual/365.0
slippage_pct = slippage_bps/10000.0
net_pct = net_daily_pct(funding_daily, borrow_daily, maker_fee, taker_fee, slippage_pct)

st.subheader("Funding Carry (1:1 Hedge) — Paper")
colA, colB, colC = st.columns(3)
colA.metric("Funding Daily %", f"{funding_daily*100:.3f}%")
colB.metric("Net Daily % (after costs)", f"{net_pct*100:.3f}%")
colC.metric("Threshold", f"{min_net_daily_pct*100:.3f}%")

if "carry_open" not in st.session_state:
    st.session_state.carry_open = False
    st.session_state.cash = float(equity)
    st.session_state.notional = 0.0

notional_usd = st.number_input("Hedge Notional ($)", 0.0, equity*max_lev, min(equity*0.5, equity*max_lev), 100.0, format="%.2f")

btn_enter, btn_accrue, btn_exit = st.columns(3)
if btn_enter.button("Enter Carry (Auto)"):
    if not st.session_state.carry_open:
        if net_pct >= min_net_daily_pct:
            fee_enter = notional_usd * (maker_fee + slippage_pct)
            if st.session_state.cash >= notional_usd + fee_enter:
                st.session_state.cash -= (notional_usd + fee_enter)
                st.session_state.notional = notional_usd
                st.session_state.carry_open = True
            else:
                st.warning("Not enough cash to open that notional.")
        else:
            st.warning("Net daily % below threshold.")
    else:
        st.info("Carry already open.")

if btn_accrue.button("Accrue 1 Day Funding") and st.session_state.carry_open:
    carry = (funding_daily - borrow_daily) * st.session_state.notional
    st.session_state.cash += carry
    st.success(f"Accrued: ${carry:,.2f}")

if btn_exit.button("Exit Carry") and st.session_state.carry_open:
    fee_exit = st.session_state.notional * (taker_fee + slippage_pct)
    st.session_state.cash += (st.session_state.notional - fee_exit)
    st.session_state.notional = 0.0
    st.session_state.carry_open = False

eq_now = st.session_state.cash
cX, cY, cZ = st.columns(3)
cX.metric("Equity ($)", f"{eq_now:,.2f}")
cY.metric("Notional ($)", f"{st.session_state.notional:,.2f}")
cZ.metric("Carry Open?", "Yes" if st.session_state.carry_open else "No")

st.markdown("---")
st.caption("Educational only; not financial advice. / לשימוש לימודי בלבד; אין באמור ייעוץ השקעות.")
