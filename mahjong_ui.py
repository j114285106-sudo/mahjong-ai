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

# --- 2. 佈局排序 ---

# 第一區：選牌按鈕 (最上方)
st.markdown("### 🎯 選擇牌種")
def add_tile_logic(target):
    if not st.session_state.last_selected: return
    all_v = st.session_state.my_hand + st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis
    if all_v.count(st.session_state.last_selected) >= 4:
        st.error("此牌已達4張上限")
    else:
        target.append(st.session_state.last_selected); st.rerun()

# 九宮格選牌
for s, label in [("m", "萬"), ("t", "筒"), ("s", "條")]:
    cols = st.columns(9)
    for i in range(1, 10):
        if cols[i-1].button(f"{i}", key=f"n_{i}{s}"):
            st.session_state.last_selected = f"{i}{s}"; st.rerun()

st.markdown('<div class="zipai-row">', unsafe_allow_html=True)
z_cols = st.columns(7)
for i, name in enumerate(["東","南","西","北","中","發","白"]):
    if z_cols[i].button(name, key=f"z_{name}"):
        st.session_state.last_selected = name; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f"<p style='text-align:center; color:gold; font-size:22px;'>目前選中: {st.session_state.last_selected if st.session_state.last_selected else '-'}</p>", unsafe_allow_html=True)

# 指派對象 (將選好的牌分給各家)
st.markdown('<div class="action-row">', unsafe_allow_html=True)
a1, a2, a3, a4 = st.columns(4)
if a1.button("＋我"): add_tile_logic(st.session_state.my_hand)
if a2.button("＋上"): add_tile_logic(st.session_state.p3_dis)
if a3.button("＋對"): add_tile_logic(st.session_state.p2_dis)
if a4.button("＋下"): add_tile_logic(st.session_state.p1_dis)
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# 第二區：三家出牌與清空
st.markdown("### 👁️ 三家牌池監控")
c1, c2, c3 = st.columns(3)
with c1: 
    st.write("⬅️ 上家:", "".join(st.session_state.p3_dis))
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("清空上", key="cl3"): st.session_state.p3_dis = []; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c2: 
    st.write("⬆️ 對家:", "".join(st.session_state.p2_dis))
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("清空對", key="cl2"): st.session_state.p2_dis = []; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c3: 
    st.write("➡️ 下家:", "".join(st.session_state.p1_dis))
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("清空下", key="cl1"): st.session_state.p1_dis = []; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# 第三區：我的手牌與清空
st.markdown(f"### 🎴 我的手牌 ({len(st.session_state.my_hand)}/17)")
st.session_state.my_hand.sort()
h_row1 = st.columns(9)
for i, tile in enumerate(st.session_state.my_hand[:9]):
    if h_row1[i].button(tile, key=f"h1_{i}"): st.session_state.my_hand.pop(i); st.rerun()
h_row2 = st.columns(9)
for i, tile in enumerate(st.session_state.my_hand[9:]):
    if h_row2[i].button(tile, key=f"h2_{i}"): st.session_state.my_hand.pop(i+9); st.rerun()

st.markdown('<div class="clear-btn" style="text-align:center;">', unsafe_allow_html=True)
if st.button("🗑️ 全部清空我的手牌", key="clmy"): st.session_state.my_hand = []; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# 第四區：分析按鈕 (最下方)
st.markdown("### 🤖 戰略分析中心")
st.markdown('<div class="ai-row">', unsafe_allow_html=True)
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
