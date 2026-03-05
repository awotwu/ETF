"""
ETF 投資分析儀表板 - 網頁版
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="ETF 投資分析儀表板", page_icon="🎯", layout="wide")

ETF_LIST = {
    '0050.TW': '元大台灣50',
    '0056.TW': '元大高股息',
    '00878.TW': '國泰永續高股息',
    '00919.TW': '群益台灣精選高息',
    'VOO': 'Vanguard S&P 500',
    'QQQ': '納斯達克100',
    'VTI': 'Vanguard 全市場',
    'SCHD': 'Schwab高股息',
}

@st.cache_data(ttl=3600)
def get_etf_data(ticker):
    try:
        df = yf.download(ticker, period='5y', progress=False)
        if df.empty:
            return None
        close = df['Close']
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return {'close': close, 'high': float(close.max()), 'low': float(close.min()), 'df': df}
    except Exception as e:
        return None

def analyze_etf(ticker, name):
    data = get_etf_data(ticker)
    if data is None:
        return None
    
    try:
        close = data['close']
        current = float(close.iloc[-1])
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain/loss))
        rsi_val = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
        
        # MA
        ma50 = float(close.rolling(50).mean().iloc[-1])
        ma200 = float(close.rolling(200).mean().iloc[-1])
        
        # 百分位
        pct = float((close < current).sum() / len(close) * 100)
        
        # 距離
        dist_high = (current / data['high'] - 1) * 100
        dist_low = (current / data['low'] - 1) * 100
        
        # 評分
        score = 0
        reasons_buy = []
        reasons_no = []
        
        if pct < 25:
            score += 3
            reasons_buy.append("歷史低點")
        elif pct < 40:
            score += 1
            reasons_buy.append("偏低")
        elif pct > 85:
            score -= 3
            reasons_no.append("歷史高點")
        elif pct > 70:
            score -= 1
            reasons_no.append("相對高點")
        
        if rsi_val < 30:
            score += 2
            reasons_buy.append("RSI超賣")
        elif rsi_val > 70:
            score -= 2
            reasons_no.append("RSI超買")
        
        if current > ma200:
            score += 1
            reasons_buy.append("站上年線")
        else:
            score -= 1
            reasons_no.append("跌破年線")
        
        if ma50 > ma200:
            score += 1
            reasons_buy.append("多頭排列")
        
        if score >= 3:
            rec, action = "🟢 買進", "分批進場"
        elif score >= 1:
            rec, action = "🟡 觀望", "等回檔"
        elif score >= -1:
            rec, action = "🟠 謹慎", "小量試單"
        else:
            rec, action = "🔴 建議等", "等更低"
        
        return {
            'name': name, 'ticker': ticker, 'price': current,
            'high': data['high'], 'low': data['low'], 'pct': pct,
            'rsi': rsi_val, 'ma50': ma50, 'ma200': ma200,
            'dist_high': dist_high, 'dist_low': dist_low,
            'score': score, 'rec': rec, 'action': action,
            'reasons_buy': reasons_buy, 'reasons_no': reasons_no
        }
    except Exception as e:
        return None

st.title("🎯 ETF 投資分析儀表板")
st.markdown("**最後更新：** " + datetime.now().strftime("%Y-%m-%d %H:%M"))

selected_etfs = st.multiselect("選擇 ETF", list(ETF_LIST.keys()), 
    default=list(ETF_LIST.keys()), format_func=lambda x: ETF_LIST[x])

results = [analyze_etf(t, ETF_LIST[t]) for t in selected_etfs]
results = sorted([r for r in results if r], key=lambda x: x['score'], reverse=True)

st.header("🏆 買進排名")
cols = st.columns(4)
for i, r in enumerate(results[:4]):
    with cols[i]:
        st.metric(f"#{i+1} {r['name']}", f"${r['price']:.2f}", r['rec'])

st.subheader("📊 完整數據")
table_data = [{'ETF': r['name'], '代號': r['ticker'], '現價': f"${r['price']:.2f}",
    '5年高': f"${r['high']:.2f}", '5年低': f"${r['low']:.2f}",
    '距高點': f"{r['dist_high']:.1f}%", '距低點': f"+{r['dist_low']:.0f}%",
    '歷史百分位': f"{r['pct']:.0f}%", 'RSI': f"{r['rsi']:.0f}",
    '評分': r['score'], '結論': r['rec'], '建議': r['action']} for r in results]
st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

st.header("💡 行動建議")
buys = [r for r in results if r['score'] >= 2]
holds = [r for r in results if 0 <= r['score'] < 2]
avoid = [r for r in results if r['score'] < 0]

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### 🟢 可買進")
    if buys:
        for r in buys: st.write(f"- **{r['name']}**")
    else: st.write("無")
with c2:
    st.markdown("### 🟡 觀望")
    if holds:
        for r in holds: st.write(f"- **{r['name']}**")
    else: st.write("無")
with c3:
    st.markdown("### 🔴 建議等")
    if avoid:
        for r in avoid: st.write(f"- **{r['name']}**")
    else: st.write("無")

st.warning("⚠️ 投資風險提示：本分析僅供參考，不構成投資建議")
st.markdown(f"**數據來源：Yahoo Finance | 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}**")
