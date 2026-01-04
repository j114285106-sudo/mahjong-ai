import streamlit as st
import collections
import pandas as pd
import random
import numpy as np
import cv2
from inference_sdk import InferenceHTTPClient

# --- 1. 基礎設定與 Roboflow 初始化 ---
st.set_page_config(page_title="麻將 AI 控制台", layout="wide")

CLIENT = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key="cUeAQuPgQiWwm4oneikb")
MODEL_ID = "mahjong-vtacs/1"
TILE_MAP = {
    '1m':'1m','2m':'2m','3m':'3m','4m':'4m','5m':'5m','6m':'6m','7m':'7m','8m':'8m','9m':'9m',
    '1s':'1s','2s':'2s','3s':'3s','4s':'4s','5s':'5s','6s':'6s','7s':'7s','8s':'8s','9s':'9s',
    '1t':'1t','2t':'2t','3t':'3t','4t':'4t','5t':'5t','6t':'6t','7t':'7t','8t':'8t','9t':'9t',
    'east':'東','south':'南','west':'西','north':'北','zhong':'中','fa':'發','bai':'白'
}

# --- 2. CSS 樣式 (維持淺藍色，優化九宮格) ---
st.markdown("""
    <style>
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}

    /* 強制九宮格不換行 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
    }
    [data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; }

    /* 按鈕樣式：黑框扁平化 */
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
    }

    /* 四家監控區樣式 */
    .monitor-card {
        background-color: white;
        border: 1px solid black;
        padding: 8px;
        min-height: 80px;
    }
    .tile-text {
        font-weight: bold;
        color: black;
        font-size: 16px;
        word-break: break-all;
    }
    
    /* AI 模擬大按鈕 */
    .ai-row button { background-color: #00B050 !important; color: white !important; height: 60px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心 AI 邏輯 (蒙地卡羅模擬) ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key not in ['last_selected', 'ai_res'] else ""

def can_hu(hand):
    if len(hand) < 2: return False
    counts = collections.Counter(hand)
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
                counts[f]+=1; counts[f"{v+1}{s}"]+=1; counts[f"{v+2}{s}"]+=1
        return False
    for t in sorted(counts.keys()):
        if counts[t] >= 2:
            counts[t] -= 2
            if solve(sorted(list(counts.elements()))): return True
            counts[t] += 2
    return False

def monte_carlo_simulation(hand, visible_counts, trials=1000):
    all_tiles = ([f"{i}{s}" for i in range(1, 10) for s in ['m','t','s']] + ["東","南","西","北","中","發","白"]) * 4
    for t, c in visible_counts.items():
        for _ in range(c): 
            if t in all_tiles: 
                try: all_tiles.remove(t)
                except: pass
    results = {}
    for discard in set(hand):
        wins = 0
        temp = hand.copy(); temp.remove(discard)
        for _ in range(trials):
            wall = random.sample(all_tiles, min(len(all_tiles), 15))
            sim_h = temp.copy()
            for draw in wall:
                sim_h.append(draw)
                if can_hu(sim_h): wins += 1; break
                sim_h.pop()
        results[discard] = wins
    return results

# --- 4. 介面佈局 ---

# A. 選牌九宮格
st.markdown("### 🎯 選擇牌種")
def draw_tile_grid(labels, g_key):
    cols = st.columns(len(labels))
    for i, lb in enumerate(labels):
        if cols[i].button(lb, key=f"{g_key}_{i}"):
            st.session_state.last_selected = lb; st.rerun()

draw_tile_grid(["1m","2m","3m","4m","5m","6m","7m","8m","9m"], "m")
draw_tile_grid(["1s","2s","3s","4s","5s","6s","7s","8s","9s"], "s")
draw_tile_grid(["1t","2t","3t","4t","5t","6t","7t","8t","9t"], "t")
draw_tile_grid(["東","南","西","北","中","發","白"], "z")

st.write("")

# B. 功能按鈕
c_act = st.columns(4)
def add_tile_logic(target):
    if st.session_state.last_selected: target.append(st.session_state.last_selected); st.rerun()

if c_act[0].button("+我"): add_tile_logic(st.session_state.my_hand)
if c_act[1].button("+下家"): add_tile_logic(st.session_state.p1_dis)
if c_act[2].button("+對家"): add_tile_logic(st.session_state.p2_dis)
if c_act[3].button("+上家"): add_tile_logic(st.session_state.p3_dis)

# C. 四家監視器 (圖片 1 排版：上、對、下、我並排)
st.divider()
st.markdown("### 👁️ 全場監控 (字元顯示)")
m_cols = st.columns(4)
titles = ["⬅️ 上家", "⬆️ 對家", "➡️ 下家", "🎴 我的手牌"]
targets = ["p3_dis", "p2_dis", "p1_dis", "my_hand"]

for i in range(4):
    with m_cols[i]:
        st.markdown(f'<div class="monitor-card"><p style="font-weight:bold;margin:0;">{titles[i]}</p>', unsafe_allow_html=True)
        content = " ".join(st.session_state[targets[i]]) if st.session_state[targets[i]] else "-"
        st.markdown(f'<p class="tile-text">{content}</p></div>', unsafe_allow_html=True)
        if st.button(f"清空", key=f"cl_{i
