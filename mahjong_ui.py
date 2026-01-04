import streamlit as st
import collections
import pandas as pd
import random
import numpy as np
import cv2
from inference_sdk import InferenceHTTPClient

# --- 1. 基礎設定與 Roboflow 初始化 ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")

CLIENT = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key="cUeAQuPgQiWwm4oneikb")
MODEL_ID = "mahjong-vtacs/1"
TILE_MAP = {
    '1m':'1m','2m':'2m','3m':'3m','4m':'4m','5m':'5m','6m':'6m','7m':'7m','8m':'8m','9m':'9m',
    '1s':'1s','2s':'2s','3s':'3s','4s':'4s','5s':'5s','6s':'6s','7s':'7s','8s':'8s','9s':'9s',
    '1t':'1t','2t':'2t','3t':'3t','4t':'4t','5t':'5t','6t':'6t','7t':'7t','8t':'8t','9t':'9t',
    'east':'東','south':'南','west':'西','north':'北','zhong':'中','fa':'發','bai':'白'
}

# --- 2. CSS 樣式 (完全依照圖片1佈局) ---
st.markdown("""
    <style>
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}

    /* 九宮格不換行 */
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; gap: 2px !important; }
    [data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; }

    /* 按鈕樣式：黑框扁平 */
    div.stButton > button {
        background-color: #F0F0F0 !important;
        color: black !important;
        border: 1px solid black !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        width: 100% !important;
        aspect-ratio: 1.1 / 1;
        font-size: clamp(8px, 2.5vw, 16px) !important;
        padding: 0px !important;
    }

    /* 三家監視器 (白底黑框) */
    .mon-row { display: flex; border: 1px solid black; background-color: white; height: 35px; margin-top: -1px; }
    .mon-label { width: 50px; background-color: #D1F0FA; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; color: black; flex-shrink: 0; }
    .mon-content { flex-grow: 1; display: flex; align-items: center; padding-left: 10px; font-weight: bold; color: black; font-size: 14px; }

    /* 手牌顯示框 */
    .hand-display { background-color: #EEEEEE; border: 1px solid black; min-height: 50px; padding: 5px; font-weight: bold; font-size: 18px; color: black; margin-bottom: 5px; }

    /* AI 模擬區塊 (縮小並靠左) */
    .ai-btn-style button { background-color: #00B050 !important; color: white !important; height: 80px !important; width: 80px !important; aspect-ratio: 1/1 !important; font-size: 18px !important; border: none !important; }
    .ai-res-box { flex-grow: 1; background-color: #D9EAD3; border: 1px dashed black; height: 120px; padding: 8px; color: black; font-size: 12px; overflow-y: auto; }

    /* 隱藏相機元件的巨大佔位空間 */
    [data-testid="stCameraInput"] { position: fixed; bottom: -1000px; } 
    .custom-snap-area { margin-top: 10px; display: flex; justify-content: space-between; align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心邏輯 ---
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
    results = []
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
        results.append({"牌": discard, "勝次": wins})
    return sorted(results, key=lambda x: x["勝次"], reverse=True)

# --- 4. 介面佈局 (依照圖片1) ---

# A. 選牌區
def draw_grid(labels, g_key):
    cols = st.columns(len(labels))
    for i, lb in enumerate(labels):
        if cols[i].button(lb, key=f"{g_key}_{i}"):
            st.session_state.last_selected = lb; st.rerun()

draw_grid(["一萬","二萬","三萬","四萬","五萬","六萬","七萬","八萬","九萬"], "m")
draw_grid(["一條","二條","三條","四條","五條","六條","七條","八條","九條"], "s")
draw_grid(["一筒","二筒","三筒","四筒","五筒","六筒","七筒","八筒","九筒"], "t")
z_cols = st.columns(7)
for i, lb in enumerate(["東","南","西","北","中","發","白"]):
    if z_cols[i].button(lb, key=f"z_{i}"):
        st.session_state.last_selected = lb; st.rerun()

st.write("")

# B. 功能按鈕
c_act = st.columns(4)
def add_t(target):
    if st.session_state.last_selected: target.append(st.session_state.last_selected); st.rerun()

if c_act[0].button("+我"): add_t(st.session_state.my_hand)
if c_act[1].button("+下家"): add_t(st.session_state.p1_dis)
if c_act[2].button("+對家"): add_t(st.session_state.p2_dis)
if c_act[3].button("+上家"): add_t(st.session_state.p3_dis)

st.write("")

# C. 三家監視器
st.markdown(f'<div class="mon-row"><div class="mon-label">下家</div><div class="mon-content">{" ".join(st.session_state.p1_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mon-row"><div class="mon-label">對家</div><div class="mon-content">{" ".join(st.session_state.p2_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mon-row"><div class="mon-label">上家</div><div class="mon-content">{" ".join(st.session_state.p3_dis)}</div></div>', unsafe_allow_html=True)

# D. 我的手牌區域 (含拍照隱藏觸發)
hand_count = len(st.session_state.my_hand)
st.markdown(f'<div class="custom-snap-area"><h3 style="margin:0;">我的手牌({hand_count}/17)</h3></div>', unsafe_allow_html=True)

col_cam1, col_cam2, col_cam3 = st.columns([3, 1, 1])
with col_cam2: st.button("鏡頭")
with col_cam3: 
    # 此處利用一個小技巧：讓使用者點擊自定義按鈕，但實質上是呼叫底部的隱藏相機
    st.markdown('<label for="hidden-cam" style="cursor:pointer; background:#AAAAAA; padding:5px 10px; border:1px solid black; font-weight:bold;">拍照</label>', unsafe_allow_html=True)

# 真正的相機組件 (隱藏在底部，點擊上面 label 會觸發)
cap_img = st.camera_input("拍照", key="hidden-cam", label_visibility="collapsed")

if cap_img:
    with st.spinner('辨識中...'):
        file_bytes = np.asarray(bytearray(cap_img.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        cv2.imwrite("scan.jpg", img)
        result = CLIENT.infer("scan.jpg", model_id=MODEL_ID)
        if "predictions" in result:
            preds = result["predictions"]
            preds.sort(key=lambda x: x["x"])
            st.session_state.my_hand = [TILE_MAP.get(p["class"], p["class"]) for p in preds]
            st.rerun()

st.markdown(f'<div class="hand-display">{" ".join(st.session_state.my_hand)}</div>', unsafe_allow_html=True)
if st.button("🗑️ 清空手牌"): st.session_state.my_hand = []; st.rerun()

# E. 底部 AI 模擬區塊
ai_c1, ai_c2 = st.columns([1, 3])
with ai_c1:
    st.markdown('<div class="ai-btn-style">', unsafe_allow_html=True)
    if st.button("AI模擬"):
        with st.spinner('模擬中...'):
            v = collections.Counter(st.session_state.my_hand + st.session_state.p1_dis + st.session_state.p2_dis + st.session_state.p3_dis)
            st.session_state.ai_res = monte_carlo_simulation(st.session_state.my_hand, v)
    st.markdown('</div>', unsafe_allow_html=True)

with ai_c2:
    if st.session_state.ai_res:
        res_text = "\n".join([f"{item['牌']}: 勝次 {item['勝次']}" for item in st.session_state.ai_res[:5]])
        st.markdown(f'<div class="ai-res-box"><b>模擬 1000 回結果：</b><br>{res_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ai-res-box">等待模擬指令...</div>', unsafe_allow_html=True)
