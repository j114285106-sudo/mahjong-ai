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

# --- 2. 頁面配置與圖形化 CSS ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")

st.markdown("""
    <style>
    /* 全域背景色 */
    .stApp { background-color: #C1E6F3 !important; }
    
    /* 隱藏 Streamlit 預設元件 */
    header, footer, #MainMenu {visibility: hidden;}
    
    /* 上方三家監控區塊樣式 */
    .monitor-box {
        background-color: white;
        border: 2px solid black;
        height: 40px;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
        padding-left: 10px;
        font-weight: bold;
    }
    .monitor-label {
        background-color: #D1F0FA;
        border-right: 2px solid black;
        width: 60px;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* 通用按鈕樣式覆蓋 */
    div.stButton > button {
        background-color: #F0F0F0 !important;
        color: black !important;
        border: 2px solid black !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }
    
    /* 特定功能按鈕顏色 */
    .action-btn button { background-color: #E0E0E0 !important; }
    .camera-btn button { background-color: #AAAAAA !important; color: black !important; border: none !important; height: 35px !important; font-size: 14px !important;}
    .ai-main-btn button { background-color: #00B050 !important; color: white !important; height: 100px !important; font-size: 24px !important; }

    /* 我的手牌顯示框 */
    .hand-display {
        background-color: #F2F2F2;
        border: 2px solid black;
        height: 80px;
        margin-top: 5px;
        padding: 10px;
        font-size: 20px;
    }
    
    /* AI 結果綠色區域 */
    .ai-output {
        background-color: #D9EAD3;
        border: 2px dashed black;
        height: 200px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化狀態 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key != 'last_selected' and key != 'ai_res' else ""

# --- 4. 界面布局 (照圖施工) ---

# 上方三家顯示
st.markdown(f'<div class="monitor-box"><div class="monitor-label">下家</div>{" ".join(st.session_state.p1_dis)}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="monitor-box"><div class="monitor-label">對家</div>{" ".join(st.session_state.p2_dis)}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="monitor-box"><div class="monitor-label">上家</div>{" ".join(st.session_state.p3_dis)}</div>', unsafe_allow_html=True)

st.write("") # 間隔

# 牌種選擇按鈕區
def tile_row(labels, suffix):
    cols = st.columns(len(labels))
    for i, label in enumerate(labels):
        if cols[i].button(label, key=f"btn_{label}_{suffix}"):
            st.session_state.last_selected = label; st.rerun()

tile_row(["一萬","二萬","三萬","四萬","五萬","六萬","七萬","八萬","九萬"], "m")
tile_row(["一條","二條","三條","四條","五條","六條","七條","八條","九條"], "s")
tile_row(["一筒","二筒","三筒","四筒","五筒","六筒","七筒","八筒","九筒"], "t")
tile_row(["東","南","西","北","中","發","白"], "z")

st.write("")

# 指派動作按鈕
st.markdown('<div class="action-btn">', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
def add_tile(target):
    if st.session_state.last_selected: 
        target.append(st.session_state.last_selected); st.rerun()

if c1.button("＋我"): add_tile(st.session_state.my_hand)
if c2.button("＋下家"): add_tile(st.session_state.p1_dis)
if c3.button("＋對家"): add_tile(st.session_state.p2_dis)
if c4.button("＋上家"): add_tile(st.session_state.p3_dis)
st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# 我的手牌標題與相機按鈕
h_head_1, h_head_2, h_head_3 = st.columns([4, 1, 1])
with h_head_1: st.markdown("### 我的手牌")
with h_head_2: 
    st.markdown('<div class="camera-btn">', unsafe_allow_html=True)
    if st.button("鏡頭"): pass # 未來擴充即時偵測
    st.markdown('</div>', unsafe_allow_html=True)
with h_head_3:
    st.markdown('<div class="camera-btn">', unsafe_allow_html=True)
    # 使用 Streamlit 原生相機但隱藏，透過按鈕觸發（簡化版直接顯示）
    captured_image = st.camera_input("拍照", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

# 我的手牌內容顯示框
st.markdown(f'<div class="hand-display">{" ".join(st.session_state.my_hand)}</div>', unsafe_allow_html=True)
if st.button("🗑️ 清空手牌"): st.session_state.my_hand = []; st.rerun()

st.write("")

# AI 模擬區
footer_col1, footer_col2 = st.columns([1, 3])
with footer_col1:
    st.markdown('<div class="ai-main-btn">', unsafe_allow_html=True)
    if st.button("AI模擬"):
        # 這裡放入你原本的分析邏輯，將結果存入 st.session_state.ai_res
        st.session_state.ai_res = "正在分析目前的牌局狀況...\n建議打出：一萬\n目前向聽數：2"
    st.markdown('</div>', unsafe_allow_html=True)

with footer_col2:
    st.markdown(f'<div class="ai-output">{st.session_state.ai_res}</div>', unsafe_allow_html=True)
