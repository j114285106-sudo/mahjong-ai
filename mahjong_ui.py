import streamlit as st
import collections
import pandas as pd
import random

# --- 基礎設定 ---
st.set_page_config(page_title="麻將 AI 實戰控制台", layout="wide")

# --- 🎨 iOS 修正版 CSS (解決反白與按鈕問題) ---
st.markdown("""
    <style>
    /* 確保全域背景為淺灰色，文字為深色 */
    .stApp {
        background-color: #F8F9FA !important;
    }
    
    /* 強制按鈕變為飽滿方塊 */
    div.stButton > button {
        width: 100% !important;
        height: 55px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        border: 1px solid #CCCCCC !important;
        background-color: #FFFFFF !important;
        color: #000000 !important; /* 強制文字黑色 */
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }

    /* 指派按鈕顏色 (+我, +上等) */
    .action-btn button {
        background-color: #007AFF !important;
        color: white !important;
        border: none !important;
    }

    /* 分析與模擬按鈕 */
    .analyze-btn button {
        background-color: #34C759 !important;
        color: white !important;
        height: 65px !important;
        border: none !important;
    }

    /* 強制 columns 不換行 */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 4px !important;
    }
    [data-testid="column"] {
        flex: 1 1 10% !important;
        min-width: 40px !important;
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 1. 初始化數據 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected']:
        st.session_state[key] = [] if key != 'last_selected' else ""

# --- 2. 核心大腦邏輯 ---
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

# --- 3. UI 介面 ---
st.markdown(f"### 🎯 已選: <span style='color:#007AFF'>{st.session_state.last_selected}</span>", unsafe_allow_html=True)

# 指派功能
st.markdown('<div class="action-btn">', unsafe_allow_html=True)
a1, a2, a3, a4 = st.columns(4)
curr = st.session_state.last_selected
if a1.button("＋我"):
    if curr: st.session_state.my_hand.append(curr); st.session_state.my_hand.sort(); st.rerun()
if a2.button("＋上"):
    if curr: st.session_state.p3_dis.append(curr); st.rerun()
if a3.button("＋對"):
    if curr: st.session_state.p2_dis.append(curr); st.rerun()
if a4.button("＋下"):
    if curr: st.session_state.p1_dis.append(curr); st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# 九宮格選牌
for s, label in [("m", "萬"), ("t", "筒"), ("s", "條")]:
    cols = st.columns(9)
    for i in range(1, 10):
        if cols[i-1].button(f"{i}", key=f"n_{i}{s}"):
            st.session_state.last_selected = f"{i}{s}"; st.rerun()

z_cols = st.columns(7)
for i, name in enumerate(["東","南","西","北","中","發","白"]):
    if z_cols[i].button(name, key=f"z_{name}"):
        st.session_state.last_selected = name; st.rerun()

st.divider()

# 手牌區
st.markdown(f"### 🎴 我的手牌 ({len(st.session_state.my_hand)}/17)")
h_row1 = st.columns(9)
for i, tile in enumerate(st.session_state.my_hand[:9]):
    if h_row1[i].button(tile, key=f"h1_{i}"):
        st.session_state.my_hand.pop(i); st.rerun()
h_row2 = st.columns(9)
for i, tile in enumerate(st.session_state.my_hand[9:]):
    if h_row2[i].button(tile, key=f"h2_{i}"):
        st.session_state.my_hand.pop(i+9); st.rerun()

st.divider()

# 方位監控
c1, c2, c3 = st.columns(3)
with c1: st.write("⬅️", "".join(st.session_state.p3_dis)); st.button("清上", on_click=lambda: st.session_state.p3_dis.clear())
with c2: st.write("⬆️", "".join(st.session_state.p2_dis)); st.button("清對", on_click=lambda: st.session_state.p2_dis.clear())
with c3: st.write("➡️", "".join(st.session_state.p1_dis)); st.button("清下", on_click=lambda: st.session_state.p1_dis.clear())

st.divider()

# AI 分析按鈕
st.markdown('<div class="analyze-btn">', unsafe_allow_html=True)
b1, b2 = st.columns(2)
with b1:
    if st.button("🚀 深度分析", use_container_width=True):
        visible = collections.Counter(st.session_state.my_hand + st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis)
        ans = []
        for discard in set(st.session_state.my_hand):
            temp = st.session_state.my_hand.copy(); temp.remove(discard)
            sh = get_shanten(temp)
            rem = 0
            for t in ([f"{i}{s}" for i in range(1, 10) for s in ['m','t','s']] + ["東","南","西","北","中","發","白"]):
                if get_shanten(temp + [t]) < sh or (sh==0 and can_hu(temp + [t])):
                    rem += max(0, 4 - visible[t])
            ans.append({"牌": discard, "進張": rem})
        st.table(pd.DataFrame(ans).sort_values(by="進張", ascending=False))

with b2:
    if st.button("🧠 大數據模擬", use_container_width=True):
        with st.spinner('模擬中...'):
            visible = collections.Counter(st.session_state.my_hand + st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis)
            stats = monte_carlo_simulation(st.session_state.my_hand, visible)
            df = pd.DataFrame(list(stats.items()), columns=['牌', '勝次']).sort_values(by='勝次', ascending=False)
            st.table(df)
st.markdown('</div>', unsafe_allow_html=True)
