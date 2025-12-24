import streamlit as st
import collections
import pandas as pd
import random

# --- 基礎設定 ---
st.set_page_config(page_title="麻將 AI 控制台", layout="wide")

# --- 🎨 深色模式與精準九宮格 CSS ---
st.markdown("""
    <style>
    /* 1. 全域背景設定為深色 */
    .stApp { background-color: #121212 !important; color: #FFFFFF !important; }
    
    /* 2. 強制網格佈局 */
    [data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(9, 1fr);
        gap: 5px !important;
    }
    
    /* 針對不同數量的按鈕調整網格 */
    div.zipai-row [data-testid="stHorizontalBlock"] { grid-template-columns: repeat(7, 1fr) !important; }
    div.action-row [data-testid="stHorizontalBlock"] { grid-template-columns: repeat(4, 1fr) !important; }
    div.ai-row [data-testid="stHorizontalBlock"] { grid-template-columns: repeat(2, 1fr) !important; }

    /* 3. 按鈕外觀美化 */
    div.stButton > button {
        width: 100% !important;
        height: 55px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        background-color: #333333 !important; /* 按鈕深灰色 */
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
    }
    
    /* 被選中或特殊功能按鈕 */
    div.action-row button { background-color: #007AFF !important; border: none !important; }
    div.ai-row button { background-color: #1E6F39 !important; height: 70px !important; }
    div.clear-btn button { background-color: #8E0000 !important; height: 40px !important; font-size: 14px !important; }

    /* 隱藏元素 */
    header, footer {visibility: hidden;}
    .stMarkdown h3, .stMarkdown p { color: #FFFFFF !important; }
    hr { border-color: #333 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 數據與核心邏輯 (保持不變) ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected']:
        st.session_state[key] = [] if key != 'last_selected' else ""

def can_hu(hand_17):
    if len(hand_17) != 17: return False
    counts = collections.Counter(hand_17)
    def solve(h):
        if not h: return True
        f = h[0]
        if counts[f] >= 3:
            counts[f] -= 3
            if solve([x for x in h if counts[x] > 0]): return True
            counts[f] += 3
        if len(f) == 2 and f[1] in 'mts':
            v, s = int(f[0]), f[1]
            if counts.get(f"{v+1}{s}", 0) > 0 and counts.get(f"{v+2}{s}", 0) > 0:
                counts[f]-=1; counts[f"{v+1}{s}"]-=1; counts[f"{v+2}{s}"]-=1
                if solve([x for x in h if counts[x] > 0]): return True
                counts[f]+=1; counts[f"{v+1
