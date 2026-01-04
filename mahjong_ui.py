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

# --- 2. 強化版 CSS (確保九宮格與自適應) ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}

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
        display: flex; align-items: center; justify-content: center;
    }

    .mon-row { display: flex; border: 1px solid black; background-color: white; height: 35px; margin-top: -1px; }
    .mon-label { width: 60px; background-color: #D1F0FA; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; color: black; }
    .mon-content { flex-grow: 1; display: flex; align-items: center; padding-left: 10px; font-weight: bold; color: black; font-size: 14px; }

    .ai-btn-style button { background-color: #00B050 !important; color: white !important; height: 85px !important; width: 85px !important; aspect-ratio: 1/1 !important; font-size: 18px !important; }
    .ai-res-box { flex-grow: 1; background-color: #D9EAD3; border: 1px dashed black; min-height: 100px; padding: 10px; color: black; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 狀態初始化 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key not in ['last_selected', 'ai_res'] else ""

# --- 4. 簡單 AI 預測模組函數 ---
def run_ai_analysis(hand):
    if not hand: return "請先輸入或拍照辨識手牌。"
    # 這裡可以接入更複雜的向聽數算法，目前先做基礎統計
    counts = collections.Counter(hand)
    pairs = [k for k, v in counts.items() if v >= 2]
    triplets = [k for k, v in counts.items() if v >= 3]
    
    res = f"【AI 分析結果】\n"
    res += f"● 目前張數: {len(hand)} 張\n"
    res += f"● 對子數量: {len(pairs)} 組 ({', '.join(pairs) if pairs else '無'})\n"
    res += f"● 刻子數量: {len(triplets)} 組\n"
    res += f"● 建議策略: "
    if len(hand) % 3 == 2:
        res += f"請打出隨機一張孤張進行聽牌優化。"
    else:
        res += "等待進牌中。"
    return res

# --- 5. 介面佈局 ---

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
    if st.session_state.last_selected: 
        target.append(st.session_state.last_selected)
        st.rerun()

if a_cols[0].button("+我"): add_t(st.session_state.my_hand)
if a_cols[1].button("+下家"): add_t(st.session_state.p1_dis)
if a_cols[2].button("+對家"): add_t(st.session_state.p2_dis)
if a_cols[3].button("+上家"): add_t(st.session_state.p3_dis)

# C. 三家監視器 (修正重複 Bug)
st.markdown(f'<div class="mon-row"><div class="mon-label">下家</div><div class="mon-content">{" ".join(st.session_state.p1_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mon-row"><div class="mon-label">對家</div><div class="mon-content">{" ".join(st.session_state.p2_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mon-row"><div class="mon-label">上家</div><div class="mon-content">{" ".join(st.session_state.p3_dis)}</div></div>', unsafe_allow_html=True)

# D. 我的手牌區域
st.write("")
h_col1, h_col2, h_col3 = st.columns([2.5, 0.8, 0.8])
h_count = len(st.session_state.my_hand)
with h_col1: st.markdown(f"### 我的手牌({h_count}/17)")
with h_col2: st.button("鏡頭", key="cam_ui")
with h_col3:
    # 拍照按鈕觸發辨識
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
                st.session_state.my_hand = [TILE_MAP.get(p["class"], p["class"]) for p in preds]
                st.rerun()
    except: st.error("辨識連線失敗")

st.markdown(f'<div style="background:white; border:1px solid black; min-height:50px; padding:5px; color:black; font-weight:bold; font-size:18px;">{" ".join(st.session_state.my_hand)}</div>', unsafe_allow_html=True)
if st.button("🗑️ 清空手牌"): st.session_state.my_hand = []; st.rerun()

# E. 底部 AI 模擬 (預測模組回歸)
ai_c1, ai_c2 = st.columns([1, 3])
with ai_c1:
    st.markdown('<div class="ai-btn-style">', unsafe_allow_html=True)
    if st.button("AI模擬"):
        st.session_state.ai_res = run_ai_analysis(st.session_state.my_hand)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with ai_c2:
    st.markdown(f'<div class="ai-res-box">{st.session_state.ai_res if st.session_state.ai_res else "等待模擬指令..."}</div>', unsafe_allow_html=True)
