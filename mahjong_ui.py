import streamlit as st
import collections
import pandas as pd
import numpy as np
import cv2
import random
from inference_sdk import InferenceHTTPClient

# --- 1. 初始化與 Roboflow 設定 ---
# 確保這些資訊正確，若辨識功能暫時不用，也不會影響畫面顯示
CLIENT = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key="cUeAQuPgQiWwm4oneikb")
MODEL_ID = "mahjong-vtacs/1"
TILE_MAP = {
    '1m':'1m','2m':'2m','3m':'3m','4m':'4m','5m':'5m','6m':'6m','7m':'7m','8m':'8m','9m':'9m',
    '1s':'1s','2s':'2s','3s':'3s','4s':'4s','5s':'5s','6s':'6s','7s':'7s','8s':'8s','9s':'9s',
    '1t':'1t','2t':'2t','3t':'3t','4t':'4t','5t':'5t','6t':'6t','7t':'7t','8t':'8t','9t':'9t',
    'east':'東','south':'南','west':'西','north':'北','zhong':'中','fa':'發','bai':'白'
}

# --- 2. 核心防守與模擬邏輯 ---
def get_tile_safety(tile, hand, p1, p2, p3):
    """計算單張牌的安全顏色"""
    visible = hand + p1 + p2 + p3
    counts = collections.Counter(visible)
    discards = set(p1 + p2 + p3)
    if tile in discards: return "#00FF00"  # 現物：綠色
    if tile in ["東","南","西","北","中","發","白"]:
        if counts[tile] >= 3: return "#00FF00"
        if counts[tile] == 2: return "#FFA500" # 安全：橘色
        return "#FFFFFF"
    if len(tile) == 2:
        try:
            v, s = int(tile[0]), tile[1]
            if (v > 1 and counts.get(f"{v-1}{s}")==4) or (v < 9 and counts.get(f"{v+1}{s}")==4): return "#00FF00"
            for disc in discards:
                if len(disc) == 2 and disc[1] == s:
                    dv = int(disc[0])
                    if (v==1 and dv==4) or (v==4 and dv in [1,7]) or (v==7 and dv==4): return "#FFA500"
                    if (v==2 and dv==5) or (v==5 and dv in [2,8]) or (v==8 and dv==5): return "#FFA500"
                    if (v==3 and dv==6) or (v==6 and dv in [3,9]) or (v==9 and dv==6): return "#FFA500"
        except: pass
    return "#FFFFFF"

# --- 3. 頁面配置與 CSS ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")

# 強制淺藍色底與按鈕排版
st.markdown("""
    <style>
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}
    
    /* 九宮格不換行 */
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; gap: 2px !important; }
    [data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; }
    
    /* 監視器樣式 */
    .mon-row { display: flex; border: 1px solid black; background-color: white; height: 35px; margin-top: -1px; }
    .mon-label { width: 50px; background-color: #D1F0FA; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; color: black; flex-shrink: 0; }
    .mon-content { flex-grow: 1; display: flex; align-items: center; padding-left: 10px; font-weight: bold; color: black; font-size: 14px; overflow: hidden; }
    
    /* AI 模擬區 */
    .ai-btn-style button { background-color: #00B050 !important; color: white !important; height: 80px !important; width: 80px !important; }
    .ai-res-box { flex-grow: 1; background-color: #D9EAD3; border: 1px dashed black; min-height: 100px; padding: 8px; color: black; font-size: 12px; }
    
    /* 隱藏相機元件 */
    [data-testid="stCameraInput"] { position: fixed; bottom: -1000px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 界面實作 ---
# 初始化狀態
if 'my_hand' not in st.session_state:
    st.session_state.my_hand = []
if 'p1_dis' not in st.session_state: st.session_state.p1_dis = []
if 'p2_dis' not in st.session_state: st.session_state.p2_dis = []
if 'p3_dis' not in st.session_state: st.session_state.p3_dis = []
if 'last_selected' not in st.session_state: st.session_state.last_selected = ""
if 'ai_res' not in st.session_state: st.session_state.ai_res = None

# A. 選牌九宮格
def draw_grid(labels, g_key):
    cols = st.columns(len(labels))
    for i, lb in enumerate(labels):
        if cols[i].button(lb, key=f"{g_key}_{i}"):
            st.session_state.last_selected = lb
            st.rerun()

draw_grid(["1m","2m","3m","4m","5m","6m","7m","8m","9m"], "m")
draw_grid(["1s","2s","3s","4s","5s","6s","7s","8s","9s"], "s")
draw_grid(["1t","2t","3t","4t","5t","6t","7t","8t","9t"], "t")
draw_grid(["東","南","西","北","中","發","白"], "z")

# B. 動作按鈕
st.write("")
c_act = st.columns(4)
def add_tile(target):
    if st.session_state.last_selected:
        target.append(st.session_state.last_selected)
        st.rerun()

if c_act[0].button("+我"): add_tile(st.session_state.my_hand)
if c_act[1].button("+下家"): add_tile(st.session_state.p1_dis)
if c_act[2].button("+對家"): add_tile(st.session_state.p2_dis)
if c_act[3].button("+上家"): add_tile(st.session_state.p3_dis)

# C. 三家監視器
st.write("")
st.markdown(f'<div class="mon-row"><div class="mon-label">下家</div><div class="mon-content">{" ".join(st.session_state.p1_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mon-row"><div class="mon-label">對家</div><div class="mon-content">{" ".join(st.session_state.p2_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mon-row"><div class="mon-label">上家</div><div class="mon-content">{" ".join(st.session_state.p3_dis)}</div></div>', unsafe_allow_html=True)

# D. 我的手牌區
st.write("")
h_col1, h_col2, h_col3 = st.columns([3, 1, 1])
with h_col1:
    st.markdown(f"### 我的手牌({len(st.session_state.my_hand)}/17)")
with h_col2: st.button("鏡頭", key="cam_btn")
with h_col3: st.markdown('<label for="hidden-cam" style="cursor:pointer; background:#AAAAAA; padding:5px 10px; border:1px solid black; font-weight:bold; font-size:14px; color:black;">拍照</label>', unsafe_allow_html=True)

# 隱藏相機與辨識邏輯
cap_img = st.camera_input("拍照", key="hidden-cam", label_visibility="collapsed")
if cap_img:
    file_bytes = np.asarray(bytearray(cap_img.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    cv2.imwrite("scan.jpg", img)
    result = CLIENT.infer("scan.jpg", model_id=MODEL_ID)
    if "predictions" in result:
        preds = result["predictions"]
        preds.sort(key=lambda x: x["x"])
        st.session_state.my_hand = [TILE_MAP.get(p["class"], p["class"]) for p in preds]
        st.rerun()

# --- 重要：手牌按鈕顯示區 (修正渲染問題) ---
if len(st.session_state.my_hand) > 0:
    # 建立一個容器來放手牌按鈕，使用 columns 模擬單張排列
    h_btn_cols = st.columns(max(17, len(st.session_state.my_hand)))
    for idx, tile in enumerate(st.session_state.my_hand):
        t_color = get_tile_safety(tile, st.session_state.my_hand, st.session_state.p1_dis, st.session_state.p2_dis, st.session_state.p3_dis)
        # 針對該按鈕注入顏色
        st.markdown(f"<style>div[data-testid='column']:nth-child({idx+1}) button {{ background-color: {t_color} !important; border: 1px solid #333 !important; color: black !important; }}</style>", unsafe_allow_html=True)
        if h_btn_cols[idx].button(tile, key=f"h_{idx}"):
            st.session_state.my_hand.pop(idx)
            st.rerun()
else:
    st.info("尚未加入手牌")

if st.button("🗑️ 全部清空手牌", key="cl_all"):
    st.session_state.my_hand = []
    st.rerun()

# E. AI 模擬區
st.divider()
ai_c1, ai_c2 = st.columns([1, 3])
with ai_c1:
    st.markdown('<div class="ai-btn-style">', unsafe_allow_html=True)
    if st.button("AI模擬"):
        # 簡易分析：計算安全度
        res = []
        for t in set(st.session_state.my_hand):
            c = get_tile_safety(t, st.session_state.my_hand, st
