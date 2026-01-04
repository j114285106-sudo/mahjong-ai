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
    /* 1. 強制全域背景顏色 */
    .stApp { background-color: #C1E6F3 !important; }
    
    /* 2. 隱藏預設元件 */
    header, footer, #MainMenu {visibility: hidden;}
    
    /* 3. 三家監控橫條樣式 */
    .monitor-box {
        background-color: white;
        border: 2px solid black;
        height: 45px;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
        overflow: hidden;
    }
    .monitor-label {
        background-color: #D1F0FA;
        border-right: 2px solid black;
        width: 80px;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        flex-shrink: 0;
    }
    .monitor-content {
        padding-left: 10px;
        font-weight: bold;
        font-size: 18px;
    }

    /* 4. 黑框扁平化按鈕 */
    div.stButton > button {
        background-color: #F0F0F0 !important;
        color: black !important;
        border: 2px solid black !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        width: 100%;
        height: 50px;
        margin: 0 !important;
    }
    
    /* 5. 相機與拍照按鈕樣式 */
    .camera-btn button { 
        background-color: #AAAAAA !important; 
        height: 35px !important; 
        font-size: 14px !important;
        border: 1px solid black !important;
    }
    
    /* 6. AI 模擬綠色按鈕 */
    .ai-main-btn button { 
        background-color: #00B050 !important; 
        color: white !important; 
        height: 120px !important; 
        font-size: 24px !important; 
    }

    /* 7. 我的手牌顯示框 */
    .hand-display {
        background-color: white;
        border: 2px solid black;
        min-height: 80px;
        margin-top: 5px;
        padding: 10px;
        font-size: 22px;
        font-weight: bold;
    }
    
    /* 8. AI 結果區域 */
    .ai-output {
        background-color: #D9EAD3;
        border: 2px dashed black;
        min-height: 120px;
        padding: 10px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化狀態 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key != 'last_selected' and key != 'ai_res' else ""

# --- 4. 界面布局 ---

# A. 上方三家顯示
st.markdown(f'<div class="monitor-box"><div class="monitor-label">下家</div><div class="monitor-content">{" ".join(st.session_state.p1_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="monitor-box"><div class="monitor-label">對家</div><div class="monitor-content">{" ".join(st.session_state.p2_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="monitor-box"><div class="monitor-label">上家</div><div class="monitor-content">{" ".join(st.session_state.p3_dis)}</div></div>', unsafe_allow_html=True)

st.write("") 

# B. 牌種選擇按鈕區
def tile_row(labels):
    cols = st.columns(len(labels))
    for i, label in enumerate(labels):
        if cols[i].button(label):
            st.session_state.last_selected = label; st.rerun()

tile_row(["一萬","二萬","三萬","四萬","五萬","六萬","七萬","八萬","九萬"])
tile_row(["一條","二條","三條","四條","五條","六條","七條","八條","九條"])
tile_row(["一筒","二筒","三筒","四筒","五筒","六筒","七筒","八筒","九筒"])
tile_row(["東","南","西","北","中","發","白"])

st.write("")

# C. 指派動作按鈕
c1, c2, c3, c4 = st.columns(4)
def add_tile(target):
    if st.session_state.last_selected: 
        target.append(st.session_state.last_selected); st.rerun()

if c1.button("+我"): add_tile(st.session_state.my_hand)
if c2.button("+下家"): add_tile(st.session_state.p1_dis)
if c3.button("+對家"): add_tile(st.session_state.p2_dis)
if c4.button("+上家"): add_tile(st.session_state.p3_dis)

st.write("")

# D. 我的手牌區域
st.markdown("---")
h_col1, h_col2, h_col3 = st.columns([3, 1, 1])
with h_col1: st.subheader("我的手牌")
with h_col2:
    st.markdown('<div class="camera-btn">', unsafe_allow_html=True)
    if st.button("鏡頭", key="cam_stream"): pass
    st.markdown('</div>', unsafe_allow_html=True)
with h_col3:
    st.markdown('<div class="camera-btn">', unsafe_allow_html=True)
    cap_img = st.camera_input("拍照", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

# 執行辨識邏輯
if cap_img:
    with st.spinner('辨識中...'):
        try:
            file_bytes = np.asarray(bytearray(cap_img.read()), dtype=np.uint8)
            temp_img = cv2.imdecode(file_bytes, 1)
            cv2.imwrite("temp.jpg", temp_img)
            result = CLIENT.infer("temp.jpg", model_id=MODEL_ID)
            if "predictions" in result:
                preds = result["predictions"]
