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

# --- 2. 終極自適應九宮格 CSS ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")

st.markdown("""
    <style>
    /* 全域背景 */
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}

    /* 核心九宮格容器 (橫豎轉向通用) */
    .mahjong-grid {
        display: grid;
        grid-template-columns: repeat(9, 1fr); /* 強制 9 欄 */
        gap: 2px;
        margin-bottom: 5px;
    }
    .honor-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr); /* 字牌 7 欄 */
        gap: 2px;
        margin-bottom: 10px;
    }
    .action-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr); /* 功能按鈕 4 欄 */
        gap: 5px;
        margin-bottom: 15px;
    }

    /* 按鈕樣式優化 */
    div.stButton > button {
        background-color: #F0F0F0 !important;
        color: black !important;
        border: 1px solid black !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        padding: 2px !important;
        width: 100% !important;
        aspect-ratio: 1 / 1.1; /* 保持方塊感 */
        font-size: clamp(9px, 2.8vw, 18px) !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* 三家監視器 (白底黑框) */
    .monitor-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 10px;
        background-color: white;
    }
    .monitor-row {
        display: flex;
        border: 1px solid black;
        height: 35px;
        margin-top: -1px; /* 消除重疊線條 */
    }
    .monitor-label {
        width: 60px;
        background-color: #D1F0FA;
        border-right: 1px solid black;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 14px;
        flex-shrink: 0;
    }
    .monitor-content {
        flex-grow: 1;
        display: flex;
        align-items: center;
        padding-left: 10px;
        font-weight: bold;
        color: black;
    }

    /* 我的手牌區 */
    .hand-header {
        display: flex;
        justify-content: center;
        align-items: center;
        position: relative;
        margin: 10px 0;
    }
    .cam-btns {
        position: absolute;
        right: 0;
        display: flex;
        gap: 5px;
    }
    .hand-box {
        background-color: #EEEEEE;
        border: 1px solid black;
        min-height: 50px;
        width: 100%;
        padding: 5px;
        font-weight: bold;
        font-size: 18px;
    }

    /* AI 模擬區塊 */
    .ai-container {
        display: flex;
        gap: 10px;
        margin-top: 20px;
        align-items: flex-start;
    }
    .ai-btn-style button {
        background-color: #00B050 !important;
        color: white !important;
        height: 80px !important;
        width: 80px !important;
        font-size: 18px !important;
        border: none !important;
    }
    .ai-res-box {
        flex-grow: 1;
        background-color: #D9EAD3;
        border: 1px dashed black;
        height: 150px;
        padding: 10px;
    }

    /* 隱藏相機預設樣式 */
    [data-testid="stCameraInput"] { margin-top: -20px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 狀態初始化 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key not in ['last_selected', 'ai_res'] else ""

# --- 4. 介面佈局 (依照圖片1順序) ---

# A. 牌種選擇區 (9 欄網格)
def create_grid(labels, key_prefix):
    st.markdown(f'<div class="mahjong-grid">', unsafe_allow_html=True)
    cols = st.columns(9)
    for i, label in enumerate(labels):
        if cols[i].button(label, key=f"{key_prefix}_{i}"):
            st.session_state.last_selected = label
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

create_grid(["一萬","二萬","三萬","四萬","五萬","六萬","七萬","八萬","九萬"], "m")
create_grid(["一條","二條","三條","四條","五條","六條","七條","八條","九條"], "s")
create_grid(["一筒","二筒","三筒","四筒","五筒","六筒","七筒","八筒","九筒"], "t")

# 字牌網格 (7 欄)
z_labels = ["東","南","西","北","中","發","白"]
z_cols = st.columns(7)
for i, label in enumerate(z_labels):
    if z_cols[i].button(label, key=f"z_{i}"):
        st.session_state.last_selected = label; st.rerun()

st.write("")

# B. 指派按鈕 (4 欄)
a_cols = st.columns(4)
def add_tile(target):
    if st.session_state.last_selected: target.append(st.session_state.last_selected); st.rerun()

if a_cols[0].button("+我"): add_tile(st.session_state.my_hand)
if a_cols[1].button("+下家"): add_tile(st.session_state.p1_dis)
if a_cols[2].button("+對家"): add_tile(st.session_state.p2_dis)
if a_cols[3].button("+上家"): add_tile(st.session_state.p3_dis)

# C. 三家監視器 (圖片1位置：功能按鈕下方)
st.markdown(f"""
<div class="monitor-row"><div class="monitor-label">下家</div><div class="monitor-content">{" ".join(st.session_state.p1_dis)}</div></div>
<div class="monitor-row"><div class="monitor-label">對家</div><div class="monitor-content">{" ".join(st.session_state.p2_dis)}</div></div>
<div class="monitor-row"><div class="monitor-label">上家</div><div class="monitor-content">{" ".join(st.session_state.p3_dis)}</div></div>
""", unsafe_allow_html=True)

# D. 我的手牌區域
hand_count = len(st.session_state.my_hand)
st.markdown(f"""
<div class="hand-header">
    <h2 style="margin:0;">我的手牌({hand_count}/17)</h2>
</div>
""", unsafe_allow_html=True)

# 拍照按鈕 (放在標題右側對齊)
btn_c1, btn_c2, btn_c3 = st.columns([3, 1, 1])
with btn_c2: st.button("鏡頭", key="btn_cam")
with btn_c3: st.button("拍照", key="btn_snap")

# 拍照組件
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
                    st.session_state.my_hand = detected; st.rerun()
    except: st.error("辨識失敗")

st.markdown(f'<div class="hand-box">{" ".join(st.session_state.my_hand)}</div>', unsafe_allow_html=True)
if st.button("🗑️ 清空手牌"): st.session_state.my_hand = []; st.rerun()

# E. 底部 AI 模擬區
ai_col_btn, ai_col_res = st.columns([1, 3])
with ai_col_btn:
    st.markdown('<div class="ai-btn-style">', unsafe_allow_html=True)
    if st.button("AI模擬"):
        st.session_state.ai_res = "建議打出：一萬\n進張種類：3種\n預計向聽：1"
    st.markdown('</div>', unsafe_allow_html=True)

with ai_col_res:
    st.markdown(f'<div class="ai-res-box">{st.session_state.ai_res if st.session_state.ai_res else ""}</div>', unsafe_allow_html=True)
