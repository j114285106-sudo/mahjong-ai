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

# --- 2. 強化版 CSS：支援直橫向轉向 ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")

st.markdown("""
    <style>
    /* 全域背景 */
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}

    /* 強制所有 Column 不換行且平均分布 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: stretch !important;
        gap: 1px !important;
        margin-bottom: 2px !important;
    }

    [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
    }

    /* 按鈕樣式：確保比例與字體縮放 */
    div.stButton > button {
        background-color: #F0F0F0 !important;
        color: black !important;
        border: 1px solid black !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        padding: 0px !important;
        width: 100% !important;
        aspect-ratio: 1.1 / 1; /* 微調比例接近圖片 */
        font-size: clamp(8px, 2.5vw, 18px) !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* 三家監視器區塊 */
    .monitor-box {
        background-color: white; border: 1px solid black; height: 35px;
        margin-bottom: 0px; display: flex; align-items: center; overflow: hidden;
    }
    .monitor-label {
        background-color: #D1F0FA; border-right: 1px solid black;
        width: 45px; height: 100%; display: flex; align-items: center;
        justify-content: center; font-weight: bold; font-size: 13px;
    }
    .monitor-content { padding-left: 5px; font-weight: bold; font-size: 15px; color: black; }

    /* 我的手牌標題與按鈕區 */
    .hand-header {
        display: flex; justify-content: space-between; align-items: flex-end;
        margin-top: 10px;
    }
    
    .camera-text-btn {
        background-color: #AAAAAA; color: black; border: 1px solid black;
        padding: 2px 8px; font-size: 14px; font-weight: bold; cursor: pointer;
    }

    .hand-display {
        background-color: white; border: 1px solid black; min-height: 45px;
        padding: 5px; font-size: 18px; font-weight: bold; color: black; margin-bottom: 5px;
    }

    /* AI 模擬區塊 */
    .ai-main-btn button { 
        background-color: #00B050 !important; color: white !important; 
        aspect-ratio: auto !important; height: 70px !important; font-size: 18px !important; 
    }
    .ai-output {
        background-color: #D9EAD3; border: 1px dashed black;
        height: 100px; padding: 5px; color: black; font-weight: bold;
    }

    /* 隱藏相機元件多餘間距 */
    [data-testid="stCameraInput"] { margin-top: -15px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 狀態初始化 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key not in ['last_selected', 'ai_res'] else ""

# --- 4. 界面佈局 (依照圖片順序) ---

# A. 第一部分：牌種選擇 (九宮格)
def tile_row(labels, row_key):
    cols = st.columns(len(labels))
    for i, label in enumerate(labels):
        if cols[i].button(label, key=f"sel_{row_key}_{i}"):
            st.session_state.last_selected = label
            st.rerun()

tile_row(["一萬","二萬","三萬","四萬","五萬","六萬","七萬","八萬","九萬"], "m")
tile_row(["一條","二條","三條","四條","五條","六條","七條","八條","九條"], "s")
tile_row(["一筒","二筒","三筒","四筒","五筒","六筒","七筒","八筒","九筒"], "t")
tile_row(["東","南","西","北","中","發","白"], "z")

st.write("")

# B. 第二部分：功能指派按鈕 (+我, +下家...)
c_act = st.columns(4)
def add_tile(target):
    if st.session_state.last_selected: 
        target.append(st.session_state.last_selected); st.rerun()

if c_act[0].button("+我"): add_tile(st.session_state.my_hand)
if c_act[1].button("+下家"): add_tile(st.session_state.p1_dis)
if c_act[2].button("+對家"): add_tile(st.session_state.p2_dis)
if c_act[3].button("+上家"): add_tile(st.session_state.p3_dis)

st.write("")

# C. 第三部分：三家監視器 (放在中間)
st.markdown(f'<div class="monitor-box"><div class="monitor-label">下家</div><div class="monitor-content">{" ".join(st.session_state.p1_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="monitor-box"><div class="monitor-label">對家</div><div class="monitor-content">{" ".join(st.session_state.p2_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="monitor-box"><div class="monitor-label">上家</div><div class="monitor-content">{" ".join(st.session_state.p3_dis)}</div></div>', unsafe_allow_html=True)

# D. 第四部分：我的手牌(0/17) 與相機按鈕
hand_count = len(st.session_state.my_hand)
st.write("")
h_col1, h_col2, h_col3 = st.columns([2.5, 0.8, 0.8])
with h_col1:
    st.markdown(f"<h3 style='margin:0;'>我的手牌({hand_count}/17)</h3>", unsafe_allow_html=True)
with h_col2:
    if st.button("鏡頭", key="cam_ui"): pass
with h_col3:
    if st.button("拍照", key="snap_ui"): pass

# 拍照辨識隱藏組件 (用於觸發功能)
cap_img = st.camera_input("拍照", label_visibility="collapsed")

if cap_img:
    try:
        file_bytes = np.asarray(bytearray(cap_img.read()), dtype=np.uint8)
        temp_img = cv2.imdecode(file_bytes, 1)
        cv2.imwrite("scan.jpg", temp_img)
        with st.spinner('辨識中...'):
            result = CLIENT.infer("scan.jpg", model_id=MODEL_ID)
            if "predictions" in result:
                preds = result["predictions"]
                preds.sort(key=lambda x: x["x"])
                detected = [TILE_MAP.get(p["class"], p["class"]) for p in preds]
                if detected:
                    st.session_state.my_hand = detected
                    st.rerun()
    except Exception as e:
        st.error(f"辨識連線失敗")

# 手牌顯示框
st.markdown(f'<div class="hand-display">{" ".join(st.session_state.my_hand)}</div>', unsafe_allow_html=True)
if st.button("🗑️ 清空手牌", key="cl_hand"):
    st.session_state.my_hand = []; st.rerun()

# E. 第五部分：AI 模擬
f1, f2 = st.columns([1, 3])
with f1:
    st.markdown('<div class="ai-main-btn">', unsafe_allow_html=True)
    if st.button("AI模擬", key="ai_go"):
        st.session_state.ai_res = "分析中...\n建議打出：一萬\n聽牌：三六九筒"
    st.markdown('</div>', unsafe_allow_html=True)
with f2:
    st.markdown(f'<div class="ai-output">{st.session_state.ai_res if st.session_state.ai_res else ""}</div>', unsafe_allow_html=True)
