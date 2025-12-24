import streamlit as st
import collections
import pandas as pd
import random

# --- 基礎設定 ---
st.set_page_config(page_title="麻將 AI 實戰控制台 Pro", layout="wide")

# --- 📱 手機版：九宮格與自定義佈局 CSS ---
st.markdown("""
    <style>
    /* 1. 全域按鈕大型化與字體強化 */
    div.stButton > button {
        width: 100% !important;
        height: 3.8em !important;
        font-size: 22px !important; /* 字體加大 */
        font-weight: 900 !important;
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #333 !important;
        border-radius: 8px !important;
        margin: 0px !important;
    }
    
    /* 2. 強制九宮格排版：讓 column 不再自動伸縮 */
    [data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(9, 1fr) !important; /* 強制 9 欄 */
        gap: 2px !important;
    }

    /* 3. 針對字牌設定 7 欄排版 */
    .zipai-block [data-testid="stHorizontalBlock"] {
        grid-template-columns: repeat(7, 1fr) !important;
    }

    /* 4. 針對功能按鈕 (+我, +上等) 設定 4 欄排版 */
    .action-block [data-testid="stHorizontalBlock"] {
        grid-template-columns: repeat(4, 1fr) !important;
    }

    /* 5. 修正手機版欄位間距 */
    [data-testid="column"] {
        width: auto !important;
        flex: none !important;
    }

    /* 6. 其他 UI 隱藏與顏色 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stMarkdown p { font-size: 20px !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 數據與邏輯初始化 (略，保持不變) ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected']:
        st.session_state[key] = []

# --- 核心邏輯 (can_hu, get_shanten, monte_carlo_simulation 略，請保留之前版本) ---
# [請在此處保留之前的 can_hu, get_shanten, monte_carlo_simulation 函數代碼]

# --- 3. 實戰介面佈局 ---

# 第一層：方位顯示 (橫向三等分)
st.markdown("### 👁️ 全場紀錄")
c_p3, c_p2, c_p1 = st.columns(3)
with c_p3: 
    st.write("上", "".join(st.session_state.p3_dis))
    if st.button("清", key="c3"): st.session_state.p3_dis = []; st.rerun()
with c_p2: 
    st.write("對", "".join(st.session_state.p2_dis))
    if st.button("清", key="c2"): st.session_state.p2_dis = []; st.rerun()
with c_p1: 
    st.write("下", "".join(st.session_state.p1_dis))
    if st.button("清", key="c1"): st.session_state.p1_dis = []; st.rerun()

st.divider()

# 第二層：中央控制台 (九宮格核心)
st.markdown("### 🎯 選牌與指派")

# 指派功能 (4 欄排版)
st.markdown('<div class="action-block">', unsafe_allow_html=True)
a1, a2, a3, a4 = st.columns(4)
curr = st.session_state.last_selected
if curr:
    if a1.button("＋我"): 
        if len(st.session_state.my_hand) < 17: st.session_state.my_hand.append(curr); st.session_state.my_hand.sort(); st.rerun()
    if a2.button("＋上"): st.session_state.p3_dis.append(curr); st.rerun()
    if a3.button("＋對"): st.session_state.p2_dis.append(curr); st.rerun()
    if a4.button("＋下"): st.session_state.p1_dis.append(curr); st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.write(f"當前選中: {curr if curr else '-'}")

# 萬、筒、條 (每列強制 9 欄，形成 9 宮格感)
for s in ['m', 't', 's']:
    cols = st.columns(9)
    for i in range(1, 10):
        if cols[i-1].button(f"{i}", key=f"sel_{i}{s}"):
            st.session_state.last_selected = f"{i}{s}"; st.rerun()

# 字牌 (7 欄排版)
st.markdown('<div class="zipai-block">', unsafe_allow_html=True)
z_names = ["東", "南", "西", "北", "中", "發", "白"]
z_cols = st.columns(7)
for i, name in enumerate(z_names):
    if z_cols[i].button(name, key=f"sel_{name}"):
        st.session_state.last_selected = name; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# 第三層：我的手牌 (分兩列，每列 9 個，確保按鈕大)
st.markdown(f"### 🎴 我的手牌 ({len(st.session_state.my_hand)}/17)")
h_row1 = st.columns(9)
for i, tile in enumerate(st.session_state.my_hand[:9]):
    if h_row1[i].button(tile, key=f"h1_{i}"):
        st.session_state.my_hand.pop(i); st.rerun()

h_row2 = st.columns(9)
for i, tile in enumerate(st.session_state.my_hand[9:]):
    if h_row2[i].button(tile, key=f"h2_{i}"):
        st.session_state.my_hand.pop(i+9); st.rerun()

st.divider()

# 第四層：分析按鈕
b1, b2 = st.columns(2)
# [此處保留之前的深度分析與大數據模擬觸發代碼]
