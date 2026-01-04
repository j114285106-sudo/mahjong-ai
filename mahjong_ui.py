import streamlit as st
import collections
import pandas as pd
import random
import time
from PIL import Image
import numpy as np

# --- 基礎設定 ---
st.set_page_config(page_title="Mahjong AI Mobile", layout="wide", initial_sidebar_state="collapsed")

# --- 📱 iPhone 15 Pro 風格 & Dark Mode CSS ---
st.markdown("""
    <style>
    /* 全域背景與字體 */
    .stApp { 
        background-color: #000000 !important; 
        color: #FFFFFF !important; 
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 移除頂部留白，適配手機瀏海 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* 隱藏預設選單與 Footer */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* 🀄 麻將牌按鈕樣式 (更像 App 的觸控區) */
    div.stButton > button {
        width: 100% !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        border: 1px solid #333 !important;
        background-color: #1C1C1E !important; /* iOS 深灰色 */
        color: white !important;
        transition: transform 0.1s;
    }
    div.stButton > button:active {
        transform: scale(0.95);
        background-color: #3A3A3C !important;
    }

    /* 🎮 功能按鈕區 (藍色與綠色) */
    .action-btn button { background-color: #0A84FF !important; border: none !important; }
    .ai-btn button { 
        background-color: #30D158 !important; 
        color: black !important; 
        font-weight: 800 !important;
        height: 60px !important;
        font-size: 20px !important;
        border: none !important;
    }
    
    /* 🗑️ 清除按鈕 (紅色) */
    .clear-btn button { 
        background-color: #FF453A !important; 
        height: 30px !important; 
        font-size: 12px !important; 
        padding: 0px !important;
    }

    /* 🏷️ 文字標籤 */
    .section-title {
        color: #8E8E93;
        font-size: 14px;
        font-weight: 600;
        margin-top: 10px;
        margin-bottom: 5px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 📷 鏡頭區域樣式 */
    .camera-box {
        border: 1px solid #333;
        border-radius: 15px;
        background-color: #111;
        padding: 10px;
        margin-bottom: 10px;
        text-align: center;
    }

    /* ✨ AI 建議虛線框 (核心需求) */
    .recommendation-box {
        border: 2px dashed #FFD700; /* 金色虛線 */
        border-radius: 15px;
        background-color: rgba(255, 215, 0, 0.1);
        padding: 15px;
        margin-top: 10px;
        margin-bottom: 10px;
        text-align: center;
    }
    .rec-tile {
        font-size: 24px;
        font-weight: bold;
        color: #FFD700;
        display: inline-block;
        margin: 0 10px;
    }
    .rec-score {
        font-size: 12px;
        color: #CCC;
        display: block;
    }
    
    /* 橫向排列修正 */
    [data-testid="stHorizontalBlock"] { gap: 5px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 邏輯核心 (YOLO 接口與麻將算法) ---

if 'my_hand' not in st.session_state:
    st.session_state.my_hand = []
if 'ai_recommendations' not in st.session_state:
    st.session_state.ai_recommendations = None # 儲存 AI 建議結果

# 假裝的 YOLO 辨識函數 (請在此處替換為你的 Ultralytics 模型)
def mock_yolo_inference(image, mode="hand"):
    """
    這裡模擬 AI 辨識。
    請在這裡載入你的 YOLO 模型: model = YOLO('best.pt')
    results = model(image)
    並解析回傳的 Class Name
    """
    time.sleep(1.0) # 模擬運算時間
    # 模擬回傳：如果是掃手牌，回傳隨機 5 張；掃桌子回傳隨機 1 張
    mock_tiles = [f"{random.randint(1,9)}m", f"{random.randint(1,9)}s", "東", "發"]
    if mode == "hand":
        return random.choices(mock_tiles, k=5) 
    else:
        return random.choices(mock_tiles, k=1)

# [保留原有的 can_hu, get_shanten_taiwan 等函數，為節省篇幅省略，功能不變]
# 這裡簡單 mock 一個 monte_carlo 以便展示 UI 效果
def monte_carlo_simulation_mock(hand):
    results = {}
    unique_tiles = list(set(hand))
    for t in unique_tiles:
        # 模擬勝率 0% - 20%
        results[t] = random.randint(0, 1000)
    return results

# --- 2. 介面佈局 (iPhone 優化版) ---

# 頂部：AI 建議顯示區 (虛線框) - 這是你要求的新功能
if st.session_state.ai_recommendations:
    st.markdown('<p class="section-title">✨ AI 戰術建議 (安全/勝率)</p>', unsafe_allow_html=True)
    st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
    
    # 將結果轉為 Column 排列
    cols = st.columns(len(st.session_state.ai_recommendations))
    for idx, (tile, score) in enumerate(st.session_state.ai_recommendations):
        with cols[idx]:
            st.markdown(f"""
                <div style="text-align:center;">
                    <span class="rec-tile">{tile}</span>
                    <span class="rec-score">Win: {score}</span>
                </div>
            """, unsafe_allow_html=True)
            
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- 📸 視覺辨識區 (新增的兩個按鈕) ---
# 使用 Expander 收納鏡頭畫面，避免手機版面過長
with st.expander("📷 開啟鏡頭辨識 (手牌/桌牌)", expanded=False):
    tab1, tab2 = st.tabs(["🖐️ 拍手牌", "👀 掃桌牌"])
    
    with tab1:
        st.info("按下快門，將辨識結果加入手牌")
        img_hand = st.camera_input("拍攝手牌", key="cam_hand", label_visibility="collapsed")
        if img_hand:
            # 呼叫 YOLO
            detected = mock_yolo_inference(img_hand, mode="hand")
            st.session_state.my_hand.extend(detected)
            st.success(f"已辨識並加入: {detected}")
            time.sleep(1)
            st.rerun()

    with tab2:
        st.info("掃描桌上牌，辨識後加入手牌")
        img_table = st.camera_input("掃描桌牌", key="cam_table", label_visibility="collapsed")
        if img_table:
            # 呼叫 YOLO
            detected = mock_yolo_inference(img_table, mode="table")
            st.session_state.my_hand.extend(detected)
            st.success(f"已捕捉: {detected}")
            time.sleep(1)
            st.rerun()

# --- 🎴 我的手牌區 (Grid 下方) ---
st.markdown(f'<p class="section-title">我的手牌 ({len(st.session_state.my_hand)}/17)</p>', unsafe_allow_html=True)

# 手牌顯示邏輯 (每行 9 張，適合手機寬度)
st.session_state.my_hand.sort()
if st.session_state.my_hand:
    chunk_size = 8 # iPhone 寬度較窄，建議一行 8 張
    for i in range(0, len(st.session_state.my_hand), chunk_size):
        cols = st.columns(chunk_size)
        chunk = st.session_state.my_hand[i:i+chunk_size]
        for idx, tile in enumerate(chunk):
            if cols[idx].button(tile, key=f"my_{i}_{idx}"):
                st.session_state.my_hand.pop(i+idx)
                st.rerun()
else:
    st.markdown("<div style='text-align:center; color:#555; padding:20px;'>等待輸入...</div>", unsafe_allow_html=True)

# 手牌操作工具列
c_cl, c_sim = st.columns([1, 2])
with c_cl:
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("清空", key="clr_hand"):
        st.session_state.my_hand = []
        st.session_state.ai_recommendations = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c_sim:
    # 這是你要求的「AI 模擬」按鈕
    st.markdown('<div class="ai-btn">', unsafe_allow_html=True)
    if st.button("🧠 AI 模擬"):
        if not st.session_state.my_hand:
            st.error("請先輸入手牌")
        else:
            with st.spinner("AI 計算中..."):
                # 執行模擬
                sim_result = monte_carlo_simulation_mock(st.session_state.my_hand)
                # 排序並取前 5 名
                sorted_res = sorted(sim_result.items(), key=lambda x: x[1], reverse=True)[:5]
                st.session_state.ai_recommendations = sorted_res
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- ⌨️ 手動輸入鍵盤區 (保留以防鏡頭失靈) ---
st.markdown('<p class="section-title">手動補牌</p>', unsafe_allow_html=True)
tabs_input = st.tabs(["萬", "筒", "條", "字"])

def manual_add(tile):
    if len(st.session_state.my_hand) < 17:
        st.session_state.my_hand.append(tile)
        st.rerun()

with tabs_input[0]:
    c = st.columns(9)
    for i in range(1, 10): 
        if c[i-1].button(str(i), key=f"m_{i}"): manual_add(f"{i}m")
with tabs_input[1]:
    c = st.columns(9)
    for i in range(1, 10): 
        if c[i-1].button(str(i), key=f"t_{i}"): manual_add(f"{i}t")
with tabs_input[2]:
    c = st.columns(9)
    for i in range(1, 10): 
        if c[i-1].button(str(i), key=f"s_{i}"): manual_add(f"{i}s")
with tabs_input[3]:
    c = st.columns(7)
    for i, t in enumerate(["東","南","西","北","中","發","白"]): 
        if c[i].button(t, key=f"z_{i}"): manual_add(t)
