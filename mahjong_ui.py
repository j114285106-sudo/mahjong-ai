import streamlit as st
import collections
import pandas as pd
import random

# --- 基礎設定 ---
st.set_page_config(page_title="麻將 AI 實戰控制台", layout="wide")

# --- 🎨 深色模式與緊湊佈局 CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #121212 !important; color: #FFFFFF !important; }
    
    /* 強制網格佈局 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 3px !important;
    }
    
    /* 類別標籤 */
    .label-text { color: #FFD700 !important; font-size: 16px !important; font-weight: bold; margin: 5px 0 2px 0; }

    /* 三家與我的手牌監控區 (水平並排) */
    div.monitor-row [data-testid="column"] {
        flex: 1 1 25% !important; /* 改為四等分：上、對、下、我 */
        min-width: 0px !important;
    }

    /* 按鈕樣式 */
    div.stButton > button {
        width: 100% !important;
        height: 50px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        background-color: #333333 !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
    }
    
    div.action-row button { background-color: #007AFF !important; border: none !important; }
    div.ai-row button { background-color: #1E6F39 !important; height: 65px !important; }
    div.clear-btn button { background-color: #8E0000 !important; height: 35px !important; font-size: 12px !important; border: none !important; }

    header, footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 1. 數據初始化與邏輯 (保留不變) ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected']:
        st.session_state[key] = [] if key != 'last_selected' else ""

# [請在此處保留之前的 can_hu, get_shanten, monte_carlo_simulation 函數代碼]
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

# 第一區：選牌與指派
st.markdown("### 🎯 牌種選擇與指派")

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

st.markdown(f"<p style='text-align:center; color:gold; margin:5px;'>選中: {st.session_state.last_selected if st.session_state.last_selected else '-'}</p>", unsafe_allow_html=True)

# 指派藍色按鈕區
st.markdown('<div class="action-row">', unsafe_allow_html=True)
a1, a2, a3, a4 = st.columns(4)
def add_tile_logic(target):
    if not st.session_state.last_selected: return
    all_v = st.session_state.my_hand + st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis
    if all_v.count(st.session_state.last_selected) >= 4:
        st.error("已達4張上限")
    else:
        target.append(st.session_state.last_selected); st.rerun()

if a1.button("＋我"): add_tile_logic(st.session_state.my_hand)
if a2.button("＋上"): add_tile_logic(st.session_state.p3_dis)
if a3.button("＋對"): add_tile_logic(st.session_state.p2_dis)
if a4.button("＋下"): add_tile_logic(st.session_state.p1_dis)
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# 第二區：四家水平牌池監控 (整合手牌進來)
st.markdown("### 👁️ 全場監視 (點擊牌種選中後指派)")
st.markdown('<div class="monitor-row">', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
with m1: 
    st.markdown("**⬅️ 上**")
    st.caption("".join(st.session_state.p3_dis) if st.session_state.p3_dis else "無")
    if st.button("清上", key="cl3"): st.session_state.p3_dis = []; st.rerun()
with m2: 
    st.markdown("**⬆️ 對**")
    st.caption("".join(st.session_state.p2_dis) if st.session_state.p2_dis else "無")
    if st.button("清對", key="cl2"): st.session_state.p2_dis = []; st.rerun()
with m3: 
    st.markdown("**➡️ 下**")
    st.caption("".join(st.session_state.p1_dis) if st.session_state.p1_dis else "無")
    if st.button("清下", key="cl1"): st.session_state.p1_dis = []; st.rerun()
with m4:
    st.markdown("**🎴 我**")
    st.session_state.my_hand.sort()
    st.caption("".join(st.session_state.my_hand) if st.session_state.my_hand else "無")
    if st.button("清我", key="clmy"): st.session_state.my_hand = []; st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# 第三區：手牌微調區 (為了能單張刪除，保留小按鈕)
st.markdown(f"### ✏️ 手牌修正 (點擊單張刪除)")
h_cols = st.columns(9) # 手牌修正用小一號的網格，僅在需要刪除單張時使用
for i, tile in enumerate(st.session_state.my_hand):
    if h_cols[i % 9].button(tile, key=f"edit_{i}"):
        st.session_state.my_hand.pop(i); st.rerun()

st.divider()

# 第四區：戰略分析
st.markdown("### 🤖 戰略分析")
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
