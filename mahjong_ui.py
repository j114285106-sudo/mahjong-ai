import streamlit as st
import collections
import pandas as pd
import random
import numpy as np
import cv2
from inference_sdk import InferenceHTTPClient

# --- 基礎設定 ---
st.set_page_config(page_title="麻將 AI 實戰控制台", layout="wide")

# --- 🎨 深色模式與純字元佈局 CSS ---
st.markdown("""
    <style>
    /* 全域深色背景 */
    .stApp { background-color: #121212 !important; color: #FFFFFF !important; }
    
    /* 強制九宮格不換行 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 3px !important;
    }
    
    /* 類別標籤樣式 */
    .label-text { color: #FFD700 !important; font-size: 16px !important; font-weight: bold; margin: 8px 0 2px 0; }

    /* 四家監控區 (並排) */
    div.monitor-row [data-testid="column"] {
        flex: 1 1 25% !important; 
        min-width: 0px !important;
        background-color: #1E1E1E;
        padding: 10px;
        border: 1px solid #333;
        border-radius: 5px;
    }

    /* 駭客綠字元顯示 */
    .tile-display {
        font-family: 'Courier New', monospace;
        font-size: 18px;
        color: #00FF00; 
        word-break: break-all;
        min-height: 40px;
    }

    /* 按鈕樣式：深灰色扁平化 */
    div.stButton > button {
        width: 100% !important;
        height: 45px !important;
        font-size: 16px !important;
        font-weight: bold !important;
        background-color: #333333 !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
        border-radius: 0px !important;
    }
    
    /* 特定顏色按鈕 */
    div.action-row button { background-color: #007AFF !important; border: none !important; }
    div.ai-row button { background-color: #1E6F39 !important; height: 60px !important; }
    div.clear-btn button { background-color: #8E0000 !important; height: 30px !important; font-size: 12px !important; }

    header, footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 1. 初始化與 AI 邏輯 ---
CLIENT = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key="cUeAQuPgQiWwm4oneikb")
MODEL_ID = "mahjong-vtacs/1"
TILE_MAP = {
    '1m':'1m','2m':'2m','3m':'3m','4m':'4m','5m':'5m','6m':'6m','7m':'7m','8m':'8m','9m':'9m',
    '1s':'1s','2s':'2s','3s':'3s','4s':'4s','5s':'5s','6s':'6s','7s':'7s','8s':'8s','9s':'9s',
    '1t':'1t','2t':'2t','3t':'3t','4t':'4t','5t':'5t','6t':'6t','7t':'7t','8t':'8t','9t':'9t',
    'east':'東','south':'南','west':'西','north':'北','zhong':'中','fa':'發','bai':'白'
}

if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected']:
        st.session_state[key] = [] if key != 'last_selected' else ""

# [邏輯函數：can_hu, get_shanten, monte_carlo_simulation 保持您的版本]
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

# --- 2. 佈局實作 ---

# A. 選牌區
st.markdown("### 🎯 選擇牌種")
for s, label in [("m", "萬"), ("t", "筒"), ("s", "條")]:
    st.markdown(f'<p class="label-text">{label}</p>', unsafe_allow_html=True)
    cols = st.columns(9)
    for i in range(1, 10):
        if cols[i-1].button(f"{i}", key=f"n_{i}{s}"):
            st.session_state.last_selected = f"{i}{s}"; st.rerun()

st.markdown('<p class="label-text">字牌</p>', unsafe_allow_html=True)
z_cols = st.columns(7)
for i, name in enumerate(["東","南","西","北","中","發","白"]):
    if z_cols[i].button(name, key=f"z_{name}"):
        st.session_state.last_selected = name; st.rerun()

st.markdown(f"<p style='text-align:center; color:gold;'>已選: {st.session_state.last_selected if st.session_state.last_selected else '-'}</p>", unsafe_allow_html=True)

# B. 指派區
st.markdown('<div class="action-row">', unsafe_allow_html=True)
a1, a2, a3, a4 = st.columns(4)
def add_tile_logic(target):
    if not st.session_state.last_selected: return
    target.append(st.session_state.last_selected); st.rerun()

if a1.button("＋我"): add_tile_logic(st.session_state.my_hand)
if a2.button("＋上"): add_tile_logic(st.session_state.p3_dis)
if a3.button("＋對"): add_tile_logic(st.session_state.p2_dis)
if a4.button("＋下"): add_tile_logic(st.session_state.p1_dis)
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# C. 監視器區
st.markdown("### 👁️ 全場監視器")
st.markdown('<div class="monitor-row">', unsafe_allow_html=True)
m_cols = st.columns(4)
titles = ["⬅️ 上家", "⬆️ 對家", "➡️ 下家", "🎴 我的手牌"]
targets = ["p3_dis", "p2_dis", "p1_dis", "my_hand"]

for i in range(4):
    with m_cols[i]:
        st.markdown(f"**{titles[i]}**")
        display_tiles = " ".join(st.session_state[targets[i]]) if st.session_state[targets[i]] else "-"
        st.markdown(f'<p class="tile-display">{display_tiles}</p>', unsafe_allow_html=True)
        if st.button("清空", key=f"cl_{i}"):
            st.session_state[targets[i]] = []; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 新增：相機辨識入口 ---
st.markdown("### 📷 辨識我的手牌")
cap_img = st.camera_input("拍照自動填入手牌", label_visibility="collapsed")
if cap_img:
    try:
        file_bytes = np.asarray(bytearray(cap_img.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        cv2.imwrite("scan.jpg", img)
        result = CLIENT.infer("scan.jpg", model_id=MODEL_ID)
        if "predictions" in result:
            preds = result["predictions"]
            preds.sort(key=lambda x: x["x"])
            st.session_state.my_hand = [TILE_MAP.get(p["class"], p["class"]) for p in preds]
            st.rerun()
    except: st.error("辨識失敗")

st.divider()

# D. 戰略分析
st.markdown("### 🤖 戰略分析中心")
st.markdown('<div class="ai-row">', unsafe_allow_html=True)
b1, b2 = st.columns(2)
with b1:
    if st.button("🚀 深度分析", use_container_width=True):
        v = collections.Counter(st.session_state.my_hand + st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis)
        ans = []
        for discard in set(st.session_state.my_hand):
            temp = st.session_state.my_hand.copy(); temp.remove(discard)
            sh = get_shanten(temp); rem = 0
            for t in ([f"{i}{s}" for i in range(1, 10) for s in ['m','t','s']] + ["東","南","西","北","中","發","白"]):
                if get_shanten(temp + [t]) < sh or (sh==0 and can_hu(temp + [t])): rem += max(0, 4 - v[t])
            ans.append({"牌": discard, "進張": rem})
        st.table(pd.DataFrame(ans).sort_values(by="進張", ascending=False))
with b2:
    if st.button("🧠 大數據模擬", use_container_width=True):
        with st.spinner('模擬中...'):
            v = collections.Counter(st.session_state.my_hand + st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis)
            stats = monte_carlo_simulation(st.session_state.my_hand, v)
            st.table(pd.DataFrame(list(stats.items()), columns=['牌', '勝次']).sort_values(by='勝次', ascending=False))
st.markdown('</div>', unsafe_allow_html=True)
