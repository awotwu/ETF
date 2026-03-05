"""
ETF 投資分析儀表板 - 網頁版
🎯 一看就懂 + 互動式圖表
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# 頁面設定
# ============================================================

st.set_page_config(
    page_title="ETF 投資分析儀表板",
    page_icon="🎯",
    layout="wide"
)

# ============================================================
# ETF 清單
# ============================================================

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

# ============================================================
# 數據獲取函數
# ============================================================

@st.cache_data(ttl=3600)  # 緩存1小時
def get_etf_data(ticker):
    """獲取ETF數據"""
    df = yf.download(ticker, period='5y', progress=False)
    if df.empty:
        return None
    
    # 處理數據格式
    close = df['Close']
    if hasattr(close, 'iloc') and hasattr(close.iloc[0], 'item'):
        close = close.iloc[:, 0]
    
    high = df['High']
    if hasattr(high, 'max'):
        high = high.max()
        low = df['Low'].min()
    
    return {
        'close': close,
        'high': high,
        'low': low,
        'df': df
    }

def calculate_indicators(close):
    """計算技術指標"""
    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + gain/loss))
    
    # MA
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    
    return {
        'rsi': rsi,
        'ma20': ma20,
        'ma50': ma50,
        'ma200': ma200
    }

def analyze_etf(ticker, name):
    """分析單一ETF"""
    data = get_etf_data(ticker)
    if data is None:
        return None
    
    close = data['close']
    high = data['high']
    low = data['low']
    
    current = float(close.iloc[-1])
    
    # 技術指標
    ind = calculate_indicators(close)
    rsi = float(ind['rsi'].iloc[-1])
    ma50 = float(ind['ma50'].iloc[-1])
    ma200 = float(ind['ma200'].iloc[-1])
    
    # 歷史百分位
    pct = (close < current).sum() / len(close) * 100
    
    # 距離高低點
    dist_high = (current / high - 1) * 100
    dist_low = (current / low - 1) * 100
    
    # 評分
    score = 0
    reasons_buy = []
    reasons_no = []
    
    # 百分位評分
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
    
    # RSI評分
    if rsi < 30:
        score += 2
        reasons_buy.append("RSI超賣")
    elif rsi < 40:
        score += 1
        reasons_buy.append("RSI偏低")
    elif rsi > 70:
        score -= 2
        reasons_no.append("RSI超買")
    
    # 均線評分
    if current > ma200:
        score += 1
        reasons_buy.append("站上年線")
    else:
        score -= 1
        reasons_no.append("跌破年線")
    
    if ma50 > ma200:
        score += 1
        reasons_buy.append("多頭排列")
    
    # 距離高點
    if dist_high < -25:
        score += 1
        reasons_buy.append("距離高點25%")
    
    # 結論
    if score >= 3:
        rec = "🟢 買進"
        action = "分批進場"
    elif score >= 1:
        rec = "🟡 觀望"
        action = "等回檔"
    elif score >= -1:
        rec = "🟠 謹慎"
        action = "小量試單"
    else:
        rec = "🔴 建議等"
        action = "等更低"
    
    return {
        'name': name,
        'ticker': ticker,
        'price': current,
        'high': high,
        'low': low,
        'pct': pct,
        'rsi': rsi,
        'ma50': ma50,
        'ma200': ma200,
        'dist_high': dist_high,
        'dist_low': dist_low,
        'score': score,
        'rec': rec,
        'action': action,
        'reasons_buy': reasons_buy,
        'reasons_no': reasons_no,
        'close_series': close,
        'ma50_series': ind['ma50'],
        'ma200_series': ind['ma200']
    }

# ============================================================
# 主程式
# ============================================================

st.title("🎯 ETF 投資分析儀表板")
st.markdown("**最後更新：** " + datetime.now().strftime("%Y-%m-%d %H:%M"))

# 側邊欄 - 選擇ETF
st.sidebar.header("選擇 ETF")
selected_etfs = st.sidebar.multiselect(
    "你想看哪些ETF？",
    options=list(ETF_LIST.keys()),
    default=list(ETF_LIST.keys()),
    format_func=lambda x: ETF_LIST[x]
)

# 分析選中的ETF
results = []
for ticker in selected_etfs:
    result = analyze_etf(ticker, ETF_LIST[ticker])
    if result:
        results.append(result)

if not results:
    st.error("無法載入數據，請稍後再試")
    st.stop()

# 按評分排序
results = sorted(results, key=lambda x: x['score'], reverse=True)

# ============================================================
# 買進排名
# ============================================================

st.header("🏆 買進排名")

col1, col2, col3, col4 = st.columns(4)
cols = [col1, col2, col3, col4]

for i, r in enumerate(results[:4]):
    with cols[i]:
        st.metric(
            label=f"#{i+1} {r['name']}",
            value=f"${r['price']:.2f}",
            delta=r['rec']
        )

# ============================================================
# 詳細表格
# ============================================================

st.subheader("📊 完整數據")

table_data = []
for r in results:
    table_data.append({
        'ETF': r['name'],
        '代號': r['ticker'],
        '現價': f"${r['price']:.2f}",
        '5年高': f"${r['high']:.2f}",
        '5年低': f"${r['low']:.2f}",
        '距高點': f"{r['dist_high']:.1f}%",
        '距低點': f"+{r['dist_low']:.0f}%",
        '歷史百分位': f"{r['pct']:.0f}%",
        'RSI': f"{r['rsi']:.0f}",
        '評分': r['score'],
        '結論': r['rec'],
        '建議': r['action']
    })

st.dataframe(
    pd.DataFrame(table_data),
    use_container_width=True,
    hide_index=True
)

# ============================================================
# 詳細分析
# ============================================================

st.header("📈 詳細分析")

for r in results[:4]:  # 顯示前4名
    with st.expander(f"{r['rec']} {r['name']} ({r['ticker']})", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 價格資訊")
            st.write(f"- **現價：** ${r['price']:.2f}")
            st.write(f"- **5年高點：** ${r['high']:.2f}")
            st.write(f"- **5年低點：** ${r['low']:.2f}")
            st.write(f"- **距離高點：** {r['dist_high']:.1f}%")
            st.write(f"- **距離低點：** +{r['dist_low']:.0f}%")
        
        with col2:
            st.markdown("### 📊 技術指標")
            st.write(f"- **歷史百分位：** {r['pct']:.0f}%")
            st.write(f"- **RSI (14)：** {r['rsi']:.1f}")
            st.write(f"- **MA50：** ${r['ma50']:.2f}")
            st.write(f"- **MA200：** ${r['ma200']:.2f}")
        
        # 買進/不買理由
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("### ✅ 買進理由")
            if r['reasons_buy']:
                for reason in r['reasons_buy']:
                    st.write(f"- {reason}")
            else:
                st.write("無")
        
        with col4:
            st.markdown("### ❌ 不買理由")
            if r['reasons_no']:
                for reason in r['reasons_no']:
                    st.write(f"- {reason}")
            else:
                st.write("無")
        
        st.markdown(f"### 🎯 結論：{r['rec']} - {r['action']}")

# ============================================================
# 行動建議
# ============================================================

st.header("💡 行動建議")

buys = [r for r in results if r['score'] >= 2]
holds = [r for r in results if 0 <= r['score'] < 2]
avoid = [r for r in results if r['score'] < 0]

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🟢 可買進")
    if buys:
        for r in buys:
            st.write(f"- **{r['name']}**")
    else:
        st.write("無")

with col2:
    st.markdown("### 🟡 觀望")
    if holds:
        for r in holds:
            st.write(f"- **{r['name']}**")
    else:
        st.write("無")

with col3:
    st.markdown("### 🔴 建議等")
    if avoid:
        for r in avoid:
            st.write(f"- **{r['name']}**")
    else:
        st.write("無")

# ============================================================
# 風險提示
# ============================================================

st.warning("""
⚠️ 投資風險提示：
- 本分析僅供參考，不構成投資建議
- 過去表現不代表未來報酬
- 建議做好風險分散，不要把所有資金投入單一標的
- 投資前請自行評估風險承受度
""")

# ============================================================
# 頁腳
# ============================================================

st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray;'>
    <p>🎯 ETF 投資分析儀表板 | 數據來源：Yahoo Finance</p>
    <p>最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>
""", unsafe_allow_html=True)
