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
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}
    
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
    .monitor-content { padding-left: 10px; font-weight: bold; font-size: 18px; color: black; }

    div.stButton > button {
        background-color: #F0F0F0 !important;
        color: black !important;
        border: 2px solid black !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        width: 100%;
        height: 45px;
    }
    
    .camera-btn button { 
        background-color: #AAAAAA !important; 
        height: 35px !important; 
        font-size: 14px !important;
    }
    
    .ai-main-btn button { 
        background-color: #00B050 !important; 
        color: white !important; 
        height: 100px !important; 
        font-size: 22px !important; 
    }

    .hand-display {
        background-color: white;
        border: 2px solid black;
        min-height: 70px;
        margin-top: 5px;
        padding: 10px;
        font-size: 20px;
        font-weight: bold;
        color: black;
    }
    
    .ai-output {
        background-color: #D9EAD3;
        border: 2px dashed black;
        min-height: 100px;
        padding: 10px;
        color: black;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化狀態 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key not in ['last_selected', 'ai_res'] else ""

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
        if cols[i].button(label, key=f"sel_{label}"):
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

# D. 我的手牌區域
st.markdown("---")
h_col1, h_col2, h_col3 = st.columns([3, 1, 1])
with h_col1: st.markdown("### 我的手牌")
with h_col2:
    st.markdown('<div class="camera-btn">', unsafe_allow_html=True)
    if st.button("鏡頭", key="cam_btn"): st.info("鏡頭串流準備中")
    st.markdown('</div>', unsafe_allow_html=True)
with h_col3:
    st.markdown('<div class="camera-btn">', unsafe_allow_html=True)
    cap_img = st.camera_input("拍照", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

# 辨識邏輯：處理 try-except 結構
if cap_img:
    with st.spinner('AI 辨識中...'):
        try:
            file_bytes = np.asarray(bytearray(cap_img.read()), dtype=np.uint8)
            temp_img = cv2.imdecode(file_bytes, 1)
            cv2.imwrite("temp_scan.jpg", temp_img)
            
            # 呼叫 Roboflow
            result = CLIENT.infer("temp_scan.jpg", model_id=MODEL_ID)
            
            if "predictions" in result:
                preds = result["predictions"]
                preds.sort(key=lambda x: x["x"])
                # 更新手牌
                st.session_state.my_hand = [p["class"] for p in preds]
                st.rerun()
        except Exception as e:
            st.error(f"辨識發生錯誤: {e}")

st.markdown(f'<div class="hand-display">{" ".join(st.session_state.my_hand)}</div>', unsafe_allow_html=True)
if st.button("🗑️ 清空手牌", key="clear_my"):
    st.session_state.my_hand = []
    st.rerun()

st.write("")

# E. AI 模擬與結果區
f1, f2 = st.columns([1, 2])
with f1:
    st.markdown('<div class="ai-main-btn">', unsafe_allow_html=True)
    if st.button("AI模擬", key="ai_go"):
        st.session_state.ai_res = "分析完成！\n建議打出：一萬\n剩餘進張：12張"
    st.markdown('</div>', unsafe_allow_html=True)
with f2:
    st.markdown(f'<div class="ai-output">{st.session_state.ai_res if st.session_state.ai_res else "等待指令..."}</div>', unsafe_allow_html=True)
