import streamlit as st
import collections
import pandas as pd
import random

# --- 基礎設定 ---
st.set_page_config(page_title="麻將 AI 實戰控制台 Pro", layout="wide")

# --- 📱 手機版 UI 大型按鈕 CSS ---
st.markdown("""
    <style>
    /* 1. 強制讓按鈕變大且字體清晰 */
    div.stButton > button {
        width: 100% !important;
        height: 4em !important; /* 增加按鈕高度 */
        font-size: 20px !important; /* 增加文字大小 */
        font-weight: 900 !important;
        background-color: #f0f2f6 !important;
        color: #31333F !important;
        border: 2px solid #d1d5db !important;
        border-radius: 10px !important;
        margin-bottom: 8px;
    }
    
    /* 2. 選中牌的提示文字放大 */
    .stMarkdown p {
        font-size: 18px !important;
    }

    /* 3. 方位區塊標題 */
    h3 {
        font-size: 22px !important;
        text-align: center;
    }

    /* 4. 移除多餘空白 */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 數據與邏輯 (保持不變) ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected']:
        st.session_state[key] = []

def can_hu(hand_17):
    if len(hand_17) != 17: return False
    counts = collections.Counter(hand_17)
    def solve(h):
        if not h: return True
        first = h[0]
        if counts[first] >= 3:
            counts[first] -= 3
            if solve([x for x in h if counts[x] > 0]): return True
            counts[first] += 3
        if len(first) == 2 and first[1] in 'mts':
            v, s = int(first[0]), first[1]
            if counts.get(f"{v+1}{s}", 0) > 0 and counts.get(f"{v+2}{s}", 0) > 0:
                counts[first] -= 1; counts[f"{v+1}{s}"] -= 1; counts[f"{v+2}{s}"] -= 1
                if solve([x for x in h if counts[x] > 0]): return True
                counts[first] += 1; counts[f"{v+1}{s}"] += 1; counts[f"{v+2}{s}"] += 1
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
        first = h[0]
        m1, d1 = 0, 0
        if counts[first] >= 3:
            counts[first] -= 3
            m, d = solve([x for x in h if counts[x] > 0])
            m1, d1 = max(m1, m + 1), max(d1, d)
            counts[first] += 3
        if len(first) == 2 and first[1] in 'mts':
            v, s = int(first[0]), first[1]
            if counts.get(f"{v+1}{s}", 0) > 0 and counts.get(f"{v+2}{s}", 0) > 0:
                counts[first] -= 1; counts[f"{v+1}{s}"] -= 1; counts[f"{v+2}{s}"] -= 1
                m, d = solve([x for x in h if counts[x] > 0])
                m1, d1 = max(m1, m + 1), max(d1, d)
                counts[first] += 1; counts[f"{v+1}{s}"] += 1; counts[f"{v+2}{s}"] += 1
        if counts[first] >= 2:
            counts[first] -= 2
            m, d = solve([x for x in h if counts[x] > 0])
            m1, d1 = max(m1, m), max(d1, d + 1)
            counts[first] += 2
        counts[first] -= 1
        m, d = solve([x for x in h if counts[x] > 0])
        m1, d1 = max(m1, m), max(d1, d)
        counts[first] += 1
        return m1, d1
    m, d = solve(sorted(list(counts.elements())))
    return max(0, 8 - (m * 2) - d)

def monte_carlo_simulation(hand, visible_counts, trials=1000):
    all_tiles = ([f"{i}{s}" for i in range(1, 10) for s in ['m','t','s']] + ["東","南","西","北","中","發","白"]) * 4
    for t, c in visible_counts.items():
        for _ in range(c): 
            if t in all_tiles: all_tiles.remove(t)
    simulation_results = {}
    for discard in set(hand):
        wins = 0
        temp_hand = hand.copy(); temp_hand.remove(discard)
        for _ in range(trials):
            test_wall = random.sample(all_tiles, min(len(all_tiles), 15)) 
            sim_hand = temp_hand.copy()
            for draw in test_wall:
                sim_hand.append(draw)
                if can_hu(sim_hand):
                    wins += 1; break
                sim_hand.pop()
        simulation_results[discard] = wins
    return simulation_results

# --- 3. 實戰方位佈局 ---

# 第一層：上家(左)、對家(中)、下家(右)
st.markdown("### 👁️ 三家牌池監控")
p_left, p_mid, p_right = st.columns(3)
with p_left:
    st.markdown("⬅️ 上家")
    st.caption(" ".join(st.session_state.p3_dis))
    if st.button("清空", key="cp3"): st.session_state.p3_dis = []; st.rerun()
with p_mid:
    st.markdown("⬆️ 對家")
    st.caption(" ".join(st.session_state.p2_dis))
    if st.button("清空", key="cp2"): st.session_state.p2_dis = []; st.rerun()
with p_right:
    st.markdown("➡️ 下家")
    st.caption(" ".join(st.session_state.p1_dis))
    if st.button("清空", key="cp1"): st.session_state.p1_dis = []; st.rerun()

st.divider()

# 第二層：選牌區 (中央控制台)
st.markdown("<div style='background:#333; padding:15px; border-radius:15px;'>", unsafe_allow_html=True)
st.markdown("<h3 style='color:white; margin:0;'>🎯 選牌指派</h3>", unsafe_allow_html=True)

def add_tile_logic(target):
    if not st.session_state.last_selected: return
    all_v = st.session_state.my_hand + st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis
    if all_v.count(st.session_state.last_selected) >= 4:
        st.error("已達4張上限")
    else:
        target.append(st.session_state.last_selected); st.rerun()

# 指派動作按鈕 (放大版)
a1, a2, a3, a4 = st.columns(4)
curr = st.session_state.last_selected
if curr:
    if a1.button("＋我"): add_tile_logic(st.session_state.my_hand)
    if a2.button("＋上"): add_tile_logic(st.session_state.p3_dis)
    if a3.button("＋對"): add_tile_logic(st.session_state.p2_dis)
    if a4.button("＋下"): add_tile_logic(st.session_state.p1_dis)
st.markdown(f"<p style='text-align:center; color:gold; font-size:24px;'>選取中: {curr if curr else '-'}</p>", unsafe_allow_html=True)

# 數字牌按鈕 (超大)
for s, name in [("m", "萬"), ("t", "筒"), ("s", "條")]:
    cols = st.columns(9)
    for i in range(1, 10):
        if cols[i-1].button(f"{i}", key=f"sel_{i}{s}"):
            st.session_state.last_selected = f"{i}{s}"
            st.rerun()

# 字牌按鈕 (超大)
z_names = ["東", "南", "西", "北", "中", "發", "白"]
z_cols = st.columns(7)
for i, name in enumerate(z_names):
    if z_cols[i].button(name, key=f"sel_{name}"):
        st.session_state.last_selected = name
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# 第三層：我的手牌
st.markdown(f"### 🎴 我的手牌 ({len(st.session_state.my_hand)}/17)")
st.session_state.my_hand.sort()
# 手牌在手機上分兩行顯示，確保按鈕夠大
h_rows = [st.columns(9), st.columns(8)]
for i, tile in enumerate(st.session_state.my_hand):
    row_idx = 0 if i < 9 else 1
    col_idx = i if i < 9 else i - 9
    if h_rows[row_idx][col_idx].button(tile, key=f"h_{i}"):
        st.session_state.my_hand.pop(i); st.rerun()

st.divider()

# 第四層：AI 分析
c_ai1, c_ai2 = st.columns(2)
with c_ai1:
    if st.button("🚀 深度分析", type="primary", use_container_width=True):
        all_dis = st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis
        visible = collections.Counter(st.session_state.my_hand + all_dis)
        ans = []
        for discard in set(st.session_state.my_hand):
            temp = st.session_state.my_hand.copy(); temp.remove(discard)
            sh = get_shanten(temp)
            rem = 0
            for t in [f"{i}{s}" for i in range(1, 10) for s in ['m','t','s']] + ["東","南","西","北","中","發","白"]:
                th = temp + [t]
                if get_shanten(th) < sh or (sh==0 and can_hu(th)):
                    rem += max(0, 4 - visible[t])
            ans.append({"牌": discard, "進張": rem})
        st.table(pd.DataFrame(ans).sort_values(by="進張", ascending=False))

with c_ai2:
    if st.button("🧠 大數據模擬", type="secondary", use_container_width=True):
        with st.spinner('模擬中...'):
            all_dis = st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis
            visible = collections.Counter(st.session_state.my_hand + all_dis)
            stats = monte_carlo_simulation(st.session_state.my_hand, visible)
            df_s = pd.DataFrame(list(stats.items()), columns=['牌', '勝次']).sort_values(by='勝次', ascending=False)
            st.table(df_s)
