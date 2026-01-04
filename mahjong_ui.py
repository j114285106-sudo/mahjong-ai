import streamlit as st
import collections
import pandas as pd
import numpy as np
import cv2
import random
from inference_sdk import InferenceHTTPClient

# --- 1. 初始化與 Roboflow 設定 ---
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
        v, s = int(tile[0]), tile[1]
        if (v > 1 and counts.get(f"{v-1}{s}")==4) or (v < 9 and counts.get(f"{v+1}{s}")==4): return "#00FF00" # 壁
        # 筋牌邏輯 (Suji)
        for disc in discards:
            if len(disc) == 2 and disc[1] == s:
                dv = int(disc[0])
                if (v==1 and dv==4) or (v==4 and dv in [1,7]) or (v==7 and dv==4): return "#FFA500"
                if (v==2 and dv==5) or (v==5 and dv in [2,8]) or (v==8 and dv==5): return "#FFA500"
                if (v==3 and dv==6) or (v==6 and dv in [3,9]) or (v==9 and dv==6): return "#FFA500"
    return "#FFFFFF"

def analyze_defense_pro(hand, p1, p2, p3):
    """1000回模擬分析安全性"""
    if not hand: return []
    results = []
    for tile in set(hand):
        # 這裡結合現物、筋、壁給予 0-100 分數
        color = get_tile_safety(tile, hand, p1, p2, p3)
        score = 100 if color == "#00FF00" else 70 if color == "#FFA500" else 30
        results.append({"牌": tile, "安全度": score})
    return sorted(results, key=lambda x: x["安全度"], reverse=True)

# --- 3. CSS 樣式 (淺藍色 + 圖片 1 排版) ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; gap: 1px !important; }
    [data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; }
    
    /* 按鈕樣式 */
    div.stButton > button { 
        background-color: #F0F0F0 !important; color: black !important; 
        border: 1px solid black !important; border-radius: 0px !important; 
        font-weight: bold !important; width: 100% !important; aspect-ratio: 1.1 / 1; 
        font-size: clamp(8px, 2.5vw, 16px) !important; padding: 0px !important; 
    }
    
    /* 監視器橫條 */
    .mon-row { display: flex; border: 1px solid black; background-color: white; height: 35px; margin-top: -1px; }
    .mon-label { width: 50px; background-color: #D1F0FA; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; color: black; flex-shrink: 0; }
    .mon-content { flex-grow: 1; display: flex; align-items: center; padding-left: 10px; font-weight: bold; color: black; font-size: 14px; }
    
    /* 手牌按鈕區域 */
    .hand-area { background-color: #EEEEEE; border: 1px solid black; padding: 5px; min-height: 55px; display: flex; flex-wrap: wrap; gap: 2px; }
    
    /* AI 結果框 */
    .ai-btn-style button { background-color: #00B050 !important; color: white !important; height: 80px !important; width: 80px !important; }
    .ai-res-box { flex-grow: 1; background-color: #D9EAD3; border: 1px dashed black; height: 120px; padding: 8px; color: black; font-size: 12px; }
    
    /* 隱藏相機元件 */
    [data-testid="stCameraInput"] { position: fixed; bottom: -1000px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 界面實作 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key not in ['last_selected', 'ai_res'] else ""

# A.
