import streamlit as st
import collections
import pandas as pd
import numpy as np
from inference_sdk import InferenceHTTPClient
import cv2

# --- 1. Roboflow 初始化 ---
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="cUeAQuPgQiWwm4oneikb"
)
MODEL_ID = "mahjong-vtacs/1"

TILE_MAP = {
    '1m':'一萬','2m':'二萬','3m':'三萬','4m':'四萬','5m':'五萬','6m':'六萬','7m':'七萬','8m':'八萬','9m':'九萬',
    '1s':'一條','2s':'二條','3s':'三條','4s':'四條','5s':'五條','6s':'六條','7s':'七條','8s':'八條','9s':'九條',
    '1t':'一筒','2t':'二筒','3t':'三筒','4t':'四筒','5t':'五筒','6t':'六筒','7t':'七筒','8t':'八筒','9t':'九筒',
    'east':'東','south':'南','west':'西','north':'北','zhong':'中','fa':'發','bai':'白'
}

# --- 2. 終極排版 CSS (支援直橫向轉向) ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")

st.markdown("""
    <style>
    /* 強制修改背景顏色 */
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}

    /* 確保 columns 在手機上不換行，達成九宮格 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: stretch !important;
        gap: 2px !important;
    }
    [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
    }

    /* 按鈕樣式：黑框、方塊、字體自適應 */
    div.stButton > button {
        background-color: #F0F0F0 !important;
        color: black !important;
        border: 1px solid black !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        width: 100% !important;
        aspect-ratio: 1 / 1.1;
        font-size: clamp(8px, 2.5vw, 16px) !important;
        padding: 0px !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* 三家監視器樣式 (圖片 1 格式) */
    .mon-row {
        display: flex;
        border: 1px solid black;
        background-color: white;
        height: 35px;
        margin-top: -1px;
    }
    .mon-label {
        width: 60px;
        background-color: #D1F0FA;
        border-right: 1px solid black;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 13px;
        color: black;
    }
    .mon-content {
        flex-grow: 1;
        display: flex;
        align-items: center;
        padding-left: 10px;
        font-weight: bold;
        color: black;
    }

    /* AI 模擬區塊 */
    .ai-btn-style button {
        background-color: #00B050 !important;
        color: white !important;
        height: 80px !important;
        width: 80px !important;
        aspect-ratio: 1/1 !important;
    }
    .ai-res-box {
        flex-grow: 1;
        background-color: #D9EAD3;
        border: 1px dashed black;
        height: 120px;
        padding: 10px;
        color: black;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化狀態 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key not in ['last_selected', 'ai_res'] else ""

# --- 4. 介面佈局 (完全依照圖片 1 排序) ---

# A. 牌種選擇
def draw_grid(labels, g_key):
    cols = st.columns(len(labels))
    for i, lb in enumerate(labels):
        if cols[i].button(lb, key=f"{g_key}_{i}"):
            st.session_state.last_selected = lb; st.rerun()

draw_grid(["一萬","二萬","三萬","四萬","五萬","六萬","七萬","八萬","九萬"], "m")
draw_grid(["一條","二條","三條","四條","五條","六條","七條","八條","九條"], "s")
draw_grid(["一筒","二筒","三筒","四筒","五筒","六筒","七筒","八筒","九筒"], "t")
draw_grid(["東","南","西","北","中","發","白"], "z")

st.write("")

# B. 功能按鈕
a_cols = st.columns(4)
def add_t(target):
    if st.session_state.last_selected: target.append(st.session_state.last_selected); st.rerun()

if a_cols[0].button("+我"): add_t(st.session_state.my_hand)
if a_cols[1].button("+下家"): add_t(st.session_state.p1_dis)
if a_cols[2].button("+對家"): add_t(st.session_state.p2_dis)
if a_cols[3].button("+上家"): add_t(st.session_state.p3_dis)

# C. 三家監視器 (中間位置)
st.markdown(f"""
<div class="mon-row"><div class="mon-label">下家</div><div class="mon-content">{" ".join(st.session_state.p1_dis)}</div></div>
<div class="mon-row"><div class="mon-label">對家</div><div class="mon-label">對家</div><div class="mon-content">{" ".join(st.session_state.p2_dis)}</div></div>
<div class="mon-row"><div class="mon-label">上家</div><div class="mon-content">{" ".join(st.session_state.p3_dis)}</div></div>
""", unsafe_allow_html=True)

# D. 我的手牌區域
st.write("")
h_col1, h_col2, h_col3 = st.columns([3, 1, 1])
h_count = len(st.session_state.my_hand)
with h_col1: st.markdown(f"### 我的手牌({h_count}/17)")
with h_col2: st.button("鏡頭", key="cam_ui")
with h_col3: st.button("拍照", key="snap_ui")

cap_img = st.camera_input("拍照", label_visibility="collapsed")
if cap_img:
    # ... (辨識代碼同前)
    pass

st.markdown(f'<div style="background:white; border:1px solid black; min-height:50px; padding:5px; color:black; font-weight:bold;">{" ".join(st.session_state.my_hand)}</div>', unsafe_allow_html=True)
if st.button("🗑️ 清空手牌"): st.session_state.my_hand = []; st.rerun()

# E. 底部 AI 模擬
ai_c1, ai_c2 = st.columns([1, 3])
with ai_c1:
    st.markdown('<div class="ai-btn-style">', unsafe_allow_html=True)
    if st.button("AI模擬"): st.session_state.ai_res = "分析中..."; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with ai_c2:
    st.markdown(f'<div class="ai-res-box">{st.session_state.ai_res}</div>', unsafe_allow_html=True)
