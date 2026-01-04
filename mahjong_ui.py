import streamlit as st
import collections
import pandas as pd
import random
import numpy as np
from inference_sdk import InferenceHTTPClient 
import cv2

# --- 1. Roboflow 初始化 ---
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="cUeAQuPgQiWwm4oneikb"
)
MODEL_ID = "mahjong-vtacs/1"

# --- 2. 基礎設定與手機版 CSS ---
st.set_page_config(page_title="麻將 AI 實戰控制台", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #121212 !important; color: #FFFFFF !important; }
    /* 強制九宮格排版 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 3px !important;
    }
    div.stButton > button {
        width: 100% !important;
        height: 50px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        background-color: #333333 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
    }
    div.action-row button { background-color: #007AFF !important; border: none !important; }
    div.ai-row button { background-color: #1E6F39 !important; height: 65px !important; }
    div.clear-btn button { background-color: #8E0000 !important; height: 35px !important; font-size: 12px !important; }
    header, footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心邏輯函數 ---
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
                counts[f]+=1; counts[f"{v+1}{s}"]+=1; counts[f"{v+2}{s}"]+=1
        return False
    for t in sorted(counts.keys()):
        if counts[t] >= 2:
            counts[t] -= 2
            if solve(sorted(list(counts.elements()))): return True
            counts[t] += 2
    return False

def get_shanten(hand):
    counts = collections.Counter(hand)
    def solve(h):
        if not h: return 0, 0
        f = h[0]
        m1, d1 = 0, 0
        if counts[f] >= 3:
            counts[f] -= 3
            m, d = solve([x for x in h if counts[x] > 0])
            m1, d1 = max(m1, m + 1), max(d1, d)
            counts[f] += 3
        if len(f) == 2 and f[1] in 'mts':
            v, s = int(f[0]), f[1]
            if counts.get(f"{v+1}{s}", 0) > 0 and counts.get(f"{v+2}{s}", 0) > 0:
                counts[f]-=1; counts[f"{v+1}{s}"]-=1; counts[f"{v+2}{s}"]-=1
                m, d = solve([x for x in h if counts[x] > 0])
                m1, d1 = max(m1, m + 1), max(d1, d)
                counts[f]+=1; counts[f"{v+1}{s}"]+=1; counts[f"{v+2}{s}"]+=1
        if counts[f] >= 2:
            counts[f] -= 2
            m, d = solve([x for x in h if counts[x] > 0])
            m1, d1 = max(m1, m), max(d1, d + 1)
            counts[f] += 2
        counts[f] -= 1
        m, d = solve([x for x in h if counts[x] > 0])
        m1, d1 = max(m1, m), max(d1, d)
        counts[f] += 1
        return m1, d1
    m, d = solve(sorted(list(counts.elements())))
    return max(0, 8 - (m * 2) - d)

def monte_carlo_simulation(hand, visible_counts, trials=1000):
    all_tiles = ([f"{i}{s}" for i in range(1, 10) for s in ['m','t','s']] + ["東","南","西","北","中","發","白"]) * 4
    for t, c in visible_counts.items():
        for _ in range(c): 
            if t in all_tiles: all_tiles.remove(t)
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

# --- 4. 影像辨識函數 ---
def recognize_tiles(captured_file):
    file_bytes = np.asarray(bytearray(captured_file.read()), dtype=np.uint8)
    temp_img = cv2.imdecode(file_bytes, 1)
    cv2.imwrite("temp_scan.jpg", temp_img)
    result = CLIENT.infer("temp_scan.jpg", model_id=MODEL_ID)
    detected_tiles = []
    if "predictions" in result:
        preds = result["predictions"]
        preds.sort(key=lambda x: x["x"]) # 從左到右排序
        for p in preds:
            detected_tiles.append(p["class"])
    return detected_tiles

# --- 5. 初始化與介面 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected']:
        st.session_state[key] = [] if key != 'last_selected' else ""

st.markdown("### 📸 拍照掃描手牌")
captured_image = st.camera_input("請對準手牌拍照")

if captured_image:
    with st.spinner('AI 正在辨識你的手牌...'):
        try:
            tiles = recognize_
