import streamlit as st
import collections
import pandas as pd
import random

# --- 基礎設定 ---
st.set_page_config(page_title="麻將 AI 實戰分析儀", layout="wide")

# --- 🎨 iOS 極致美化 CSS ---
st.markdown("""
    <style>
    /* 1. 全域背景與文字顏色優化 */
    .stApp {
        background-color: #F2F2F7; /* iOS 系統背景色 */
    }

    /* 2. 強制按鈕變為「方塊狀」而非細長條 */
    div.stButton > button {
        width: 100% !important;
        height: 60px !important; /* 強制高度，產生方塊感 */
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 12px !important; /* iOS 圓角風格 */
        border: none !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; /* 輕微陰影 */
        transition: all 0.1s;
    }

    /* 3. 不同功能的按鈕配色 */
    /* 數字牌按鈕 */
    div[data-testid="column"] button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* 功能指派按鈕 (+我, +上等) */
    .action-btn button {
        background-color: #007AFF !important; /* iOS 藍 */
        color: white !important;
    }

    /* 分析按鈕 */
    .analyze-btn button {
        background-color: #34C759 !important; /* iOS 綠 */
        color: white !important;
        height: 70px !important;
    }

    /* 清空按鈕 */
    .clear-btn button {
        background-color: #FF3B30 !important; /* iOS 紅 */
        color: white !important;
        height: 40px !important;
        font-size: 14px !important;
    }

    /* 4. 強制九宮格佈局 (Grid) */
    [data-testid="stHorizontalBlock"] {
        gap: 6px !important;
        display: flex !important;
        flex-wrap: wrap !important;
    }
    
    /* 讓每個 column 在手機上佔據固定比例 (例如 9 欄中的 1 欄) */
    [data-testid="column"] {
        flex: 1 1 10% !important; /* 確保 9 個按鈕能排成一橫排 */
        min-width: 35px !important;
    }

    /* 5. 隱藏多餘 UI */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding: 10px !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 1. 初始化數據 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected']:
        st.session_state[key] = [] if key != 'last_selected' else ""

# --- 核心大腦邏輯 (can_hu, get_shanten, monte_carlo_simulation) ---
# [請保留你原本的這些 Function 代碼]
def can_hu(h17): #... 略
    pass
def get_shanten(h): #... 略
    pass

# --- 3. 實戰介面 ---

# 頂部：方位監視器 (卡片式設計)
st.markdown("### 🀄 全場監控")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**⬅️ 上家**")
    st.code("".join(st.session_state.p3_dis) if st.session_state.p3_dis else "無")
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("清空", key="c3"): st.session_state.p3_dis = []; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown("**⬆️ 對家**")
    st.code("".join(st.session_state.p2_dis) if st.session_state.p2_dis else "無")
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("清空", key="c2"): st.session_state.p2_dis = []; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    st.markdown("**➡️ 下家**")
    st.code("".join(st.session_state.p1_dis) if st.session_state.p1_dis else "無")
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("清空", key="c1"): st.session_state.p1_dis = []; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# 中央：九宮格選牌控制台
st.markdown(f"### 🎯 選牌: <span style='color:#007AFF'>{st.session_state.last_selected}</span>", unsafe_allow_html=True)

# 動作按鈕 (+我, +上, +對, +下)
st.markdown('<div class="action-btn">', unsafe_allow_html=True)
a1, a2, a3, a4 = st.columns(4)
curr = st.session_state.last_selected
if a1.button("＋我"): 
    if curr: st.session_state.my_hand.append(curr); st.session_state.my_hand.sort(); st.rerun()
if a2.button("＋上"): 
    if curr: st.session_state.p3_dis.append(curr); st.rerun()
if a3.button("＋對"): 
    if curr: st.session_state.p2_dis.append(curr); st.rerun()
if a4.button("＋下"): 
    if curr: st.session_state.p1_dis.append(curr); st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# 萬、筒、條 九宮格
for s, label in [("m", "萬"), ("t", "筒"), ("s", "條")]:
    cols = st.columns(9)
    for i in range(1, 10):
        if cols[i-1].button(f"{i}", key=f"btn_{i}{s}"):
            st.session_state.last_selected = f"{i}{s}"; st.rerun()

# 字牌
z_names = ["東", "南", "西", "北", "中", "發", "白"]
z_cols = st.columns(7)
for i, name in enumerate(z_names):
    if z_cols[i].button(name, key=f"btn_{name}"):
        st.session_state.last_selected = name; st.rerun()

st.divider()

# 手牌區 (分兩行大按鈕)
st.markdown(f"### 🎴 我的手牌 ({len(st.session_state.my_hand)}/17)")
h_row1 = st.columns(9)
for i, tile in enumerate(st.session_state.my_hand[:9]):
    if h_row1[i].button(tile, key=f"h1_{i}"):
        st.session_state.my_hand.pop(i); st.rerun()
h_row2 = st.columns(9)
for i, tile in enumerate(st.session_state.my_hand[9:]):
    if h_row2[i+9-9].button(tile, key=f"h2_{i}"):
        st.session_state.my_hand.pop(i+9); st.rerun()

st.divider()

# 分析區
st.markdown('<div class="analyze-btn">', unsafe_allow_html=True)
if st.button("🚀 執行 AI 深度分析分析", use_container_width=True):
    # [請在此處接上你原本的分析 logic]
    st.success("分析完成，請查看下方報表")
st.markdown('</div>', unsafe_allow_html=True)
