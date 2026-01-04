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

# 標籤轉換字典 (從 Roboflow 的標籤轉為你的中文按鈕格式)
TILE_MAP = {
    '1m':'一萬','2m':'二萬','3m':'三萬','4m':'四萬','5m':'五萬','6m':'六萬','7m':'七萬','8m':'八萬','9m':'九萬',
    '1s':'一條','2s':'二條','3s':'三條','4s':'四條','5s':'五條','6s':'六條','7s':'七條','8s':'八條','9s':'九條',
    '1t':'一筒','2t':'二筒','3t':'三筒','4t':'四筒','5t':'五筒','6t':'六筒','7t':'七筒','8t':'八筒','9t':'九筒',
    'east':'東','south':'南','west':'西','north':'北','zhong':'中','fa':'發','bai':'白'
}

# --- 2. 頁面配置與強制排版 CSS ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}
    
    /* 強制 columns 在手機上不換行，達成九宮格效果 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
    }
    
    /* 讓按鈕在小螢幕也能擠在一起 */
    div.stButton > button {
        background-color: #F0F0F0 !important;
        color: black !important;
        border: 2px solid black !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        font-size: 14px !important; /* 手機版字體縮小一點點 */
        padding: 0px !important;
        width: 100% !important;
        height: 45px !important;
    }

    .monitor-box {
        background-color: white; border: 2px solid black; height: 45px;
        margin-bottom: 5px; display: flex; align-items: center; overflow: hidden;
    }
    .monitor-label {
        background-color: #D1F0FA; border-right: 2px solid black;
        width: 60px; height: 100%; display: flex; align-items: center;
        justify-content: center; font-weight: bold; flex-shrink: 0;
    }
    .monitor-content { padding-left: 10px; font-weight: bold; font-size: 16px; color: black; }

    .ai-main-btn button { 
        background-color: #00B050 !important; color: white !important; 
        height: 100px !important; font-size: 20px !important; 
    }

    .hand-display {
        background-color: white; border: 2px solid black; min-height: 70px;
        margin-top: 5px; padding: 10px; font-size: 18px; font-weight: bold; color: black;
    }
    
    .ai-output {
        background-color: #D9EAD3; border: 2px dashed black;
        min-height: 100px; padding: 10px; color: black; font-weight: bold;
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

# B. 牌種選擇 (強制九宮格模式)
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

# C. 指派動作按鈕 (並排顯示)
c_act = st.columns(4)
def add_tile(target):
    if st.session_state.last_selected: 
        target.append(st.session_state.last_selected)
        st.rerun()

if c_act[0].button("+我"): add_tile(st.session_state.my_hand)
if c_act[1].button("+下家"): add_tile(st.session_state.p1_dis)
if c_act[2].button("+對家"): add_tile(st.session_state.p2_dis)
if c_act[3].button("+上家"): add_tile(st.session_state.p3_dis)

# D. 我的手牌區域與拍照功能
st.markdown("---")
h_col1, h_col2 = st.columns([3, 1])
with h_col1: st.markdown("### 我的手牌")
with h_col2:
    # 這裡放一個清空按鈕
    if st.button("🗑️ 清空", key="clear_all"):
        st.session_state.my_hand = []
        st.rerun()

# 拍照辨識
cap_img = st.camera_input("拍照辨識手牌", label_visibility="visible")

if cap_img:
    # 使用獨立的處理區塊，避免卡死
    try:
        file_bytes = np.asarray(bytearray(cap_img.read()), dtype=np.uint8)
        temp_img = cv2.imdecode(file_bytes, 1)
        cv2.imwrite("scan.jpg", temp_img)
        
        # 呼叫伺服器
        with st.spinner('AI 辨識中...'):
            result = CLIENT.infer("scan.jpg", model_id=MODEL_ID)
            
            if "predictions" in result:
                preds = result["predictions"]
                preds.sort(key=lambda x: x["x"]) # 依據左右位置排序
                # 將 Roboflow 標籤轉換為中文
                detected = [TILE_MAP.get(p["class"], p["class"]) for p in preds]
                if detected:
                    st.session_state.my_hand = detected
                    st.success(f"辨識成功！")
                    # 辨識完後清除圖片快取，防止重複執行
                    st.rerun()
    except Exception as e:
        st.error(f"連線失敗: {e}")

st.markdown(f'<div class="hand-display">{" ".join(st.session_state.my_hand)}</div>', unsafe_allow_html=True)

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
