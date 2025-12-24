import streamlit as st
import collections
import pandas as pd
import random

st.set_page_config(page_title="麻將 AI 全功能整合版", layout="wide")

# --- 📱 手機版 UI 優化代碼 (修正反白問題) ---
# --- 📱 手機版 UI 強制橫向佈局優化 ---
st.markdown("""
    <style>
    /* 1. 強制讓 columns 在手機上不換行，保持橫向排列 */
    [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
        padding: 1px !important;
    }
    
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
    }

    /* 2. 調整按鈕樣式：縮小內距以適應 9 欄排列 */
    div.stButton > button {
        width: 100% !important;
        height: 3em !important;
        padding: 0px !important;
        font-size: 14px !important; /* 稍微縮小字體以免按鈕炸開 */
        font-weight: bold !important;
        border-radius: 5px !important;
        
        /* 確保顏色清晰 */
        background-color: #f0f2f6 !important; 
        color: #31333F !important;           
        border: 1px solid #d1d5db !important;
    }

    /* 3. 我的手牌區按鈕：稍微做大一點以便單選刪除 */
    [data-testid="stExpander"] div.stButton > button {
        font-size: 12px !important;
    }

    /* 4. 隱藏不必要元素 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 1. 初始化數據 ---
for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected']:
    if key not in st.session_state: st.session_state[key] = []

# --- 2. 核心大腦邏輯 ---

def can_hu(hand_17):
    """判定 17 張牌是否胡牌 (5面子 + 1將)"""
    if len(hand_17) != 17: return False
    counts = collections.Counter(hand_17)
    
    def solve(h):
        if not h: return True
        first = h[0]
        # 1. 刻子 AAA
        if counts[first] >= 3:
            counts[first] -= 3
            if solve([x for x in h if counts[x] > 0]): return True
            counts[first] += 3
        # 2. 順子 ABC
        if len(first) == 2 and first[1] in 'mts':
            v, s = int(first[0]), first[1]
            if counts.get(f"{v+1}{s}", 0) > 0 and counts.get(f"{v+2}{s}", 0) > 0:
                counts[first] -= 1; counts[f"{v+1}{s}"] -= 1; counts[f"{v+2}{s}"] -= 1
                if solve([x for x in h if counts[x] > 0]): return True
                counts[first] += 1; counts[f"{v+1}{s}"] += 1; counts[f"{v+2}{s}"] += 1
        return False

    # 嘗試每一種對子當「將」
    tiles = sorted(counts.keys())
    for t in tiles:
        if counts[t] >= 2:
            counts[t] -= 2
            if solve(sorted(list(counts.elements()))): return True
            counts[t] += 2
    return False

def get_shanten(hand):
    """計算向聽數"""
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
    """大數據模擬引擎：模擬未來15巡的胡牌率"""
    all_tiles = ([f"{i}{s}" for i in range(1, 10) for s in ['m','t','s']] + ["東","南","西","北","中","發","白"]) * 4
    for t, c in visible_counts.items():
        for _ in range(c): 
            if t in all_tiles: all_tiles.remove(t)
    
    simulation_results = {}
    for discard in set(hand):
        wins = 0
        temp_hand = hand.copy()
        temp_hand.remove(discard)
        for _ in range(trials):
            # 隨機模擬剩下的牌牆，取15張模擬15巡
            test_wall = random.sample(all_tiles, min(len(all_tiles), 15)) 
            sim_hand = temp_hand.copy()
            for draw in test_wall:
                sim_hand.append(draw)
                # 這裡統一使用 can_hu
                if can_hu(sim_hand):
                    wins += 1
                    break
                sim_hand.pop() # 沒胡就丟掉，模擬摸打
        simulation_results[discard] = wins
    return simulation_results

# --- 3. UI 介面佈局 ---
st.title("🀄 台灣麻將 AI 實戰分析儀 (全功能整合版)")

# A. 三家牌池監控
top_c1, top_c2, top_c3 = st.columns(3)
with top_c2:
    st.markdown("### ⬆️ 對家牌池")
    st.write(" ".join(st.session_state.p2_dis) if st.session_state.p2_dis else "空")
    if st.button("🗑️ 清空對家"): st.session_state.p2_dis = []; st.rerun()

mid_c1, mid_c2, mid_c3 = st.columns([1, 2, 1])
with mid_c1:
    st.markdown("### ⬅️ 上家牌池")
    st.write(" ".join(st.session_state.p3_dis) if st.session_state.p3_dis else "空")
    if st.button("🗑️ 清空上家"): st.session_state.p3_dis = []; st.rerun()

with mid_c3:
    st.markdown("### ➡️ 下家牌池")
    st.write(" ".join(st.session_state.p1_dis) if st.session_state.p1_dis else "空")
    if st.button("🗑️ 清空下家"): st.session_state.p1_dis = []; st.rerun()

with mid_c2:
    # 中央控制台
    st.markdown("<div style='background:#222; padding:15px; border-radius:15px;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:white; text-align:center;'>🎯 中央選牌控制</h3>", unsafe_allow_html=True)
    for s, name in [("m", "萬"), ("t", "筒"), ("s", "條")]:
        cols = st.columns(9)
        for i in range(1, 10):
            tile = f"{i}{s}"
            if cols[i-1].button(f"{i}{name[0]}", key=f"sel_{tile}"):
                st.session_state.last_selected = tile
    
    z_names = ["東", "南", "西", "北", "中", "發", "白"]
    z_cols = st.columns(7)
    for i, name in enumerate(z_names):
        if z_cols[i].button(name, key=f"sel_{name}"):
            st.session_state.last_selected = name
    
    curr = st.session_state.last_selected
    st.markdown(f"<p style='text-align:center; color:gold; font-size:20px;'>目前選中: <b>{curr if curr else '請選牌'}</b></p>", unsafe_allow_html=True)
    
    def add_tile_logic(target):
        if not curr: return
        all_v = st.session_state.my_hand + st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis
        if all_v.count(curr) >= 4:
            st.error("此牌已達4張上限")
        else:
            target.append(curr); st.rerun()

    a1, a2, a3, a4 = st.columns(4)
    if curr:
        if a1.button("➕ 我手牌"):
            if len(st.session_state.my_hand) < 17: add_tile_logic(st.session_state.my_hand)
        if a2.button("➕ 上家"): add_tile_logic(st.session_state.p3_dis)
        if a3.button("➕ 對家"): add_tile_logic(st.session_state.p2_dis)
        if a4.button("➕ 下家"): add_tile_logic(st.session_state.p1_dis)
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# B. 我的手牌區
count = len(st.session_state.my_hand)
st.markdown(f"### 🎴 我的手牌 ({count} / 17)")
st.session_state.my_hand.sort()
hand_cols = st.columns(17)
for i, tile in enumerate(st.session_state.my_hand):
    if hand_cols[i].button(tile, key=f"h_{i}"):
        st.session_state.my_hand.pop(i); st.rerun()
if st.button("⚠️ 清空全部手牌"): st.session_state.my_hand = []; st.rerun()

st.divider()

# C. AI 決策中心
res_c1, res_c2 = st.columns(2)
with res_c1:
    if st.button("🚀 執行 AI 深度分析 (剩餘張數)", type="primary", use_container_width=True):
        if count == 0: st.error("請輸入手牌")
        else:
            all_dis = st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis
            visible = collections.Counter(st.session_state.my_hand + all_dis)
            hand = st.session_state.my_hand
            all_possible = [f"{i}{s}" for i in range(1, 10) for s in ['m','t','s']] + ["東","南","西","北","中","發","白"]
            ans = []
            for discard in set(hand):
                temp = hand.copy(); temp.remove(discard)
                sh = get_shanten(temp)
                rem = 0
                for t in all_possible:
                    th = temp + [t]
                    # 判斷向聽數下降或直接胡牌
                    if get_shanten(th) < sh or (sh == 0 and can_hu(th)):
                        rem += max(0, 4 - visible[t])
                ans.append({"出牌": discard, "進張": rem})
            st.table(pd.DataFrame(ans).sort_values(by="進張", ascending=False))

with res_c2:
    if st.button("🧠 啟動大數據模擬 (1000場勝率)", type="secondary", use_container_width=True):
        if count == 0: st.error("請輸入手牌")
        else:
            with st.spinner('模擬中...'):
                all_dis = st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis
                visible = collections.Counter(st.session_state.my_hand + all_dis)
                stats = monte_carlo_simulation(st.session_state.my_hand, visible)
                df_s = pd.DataFrame(list(stats.items()), columns=['出牌', '模擬勝次']).sort_values(by='模擬勝次', ascending=False)
                st.bar_chart(df_s.set_index('出牌'))

                st.table(df_s)


