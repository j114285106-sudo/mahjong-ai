import streamlit as st
import collections
import pandas as pd
import numpy as np
import cv2
from inference_sdk import InferenceHTTPClient

# --- 1. 初始化與核心防守邏輯 ---
CLIENT = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key="cUeAQuPgQiWwm4oneikb")
MODEL_ID = "mahjong-vtacs/1"
TILE_MAP = {
    '1m':'1m','2m':'2m','3m':'3m','4m':'4m','5m':'5m','6m':'6m','7m':'7m','8m':'8m','9m':'9m',
    '1s':'1s','2s':'2s','3s':'3s','4s':'4s','5s':'5s','6s':'6s','7s':'7s','8s':'8s','9s':'9s',
    '1t':'1t','2t':'2t','3t':'3t','4t':'4t','5t':'5t','6t':'6t','7t':'7t','8t':'8t','9t':'9t',
    'east':'東','south':'南','west':'西','north':'北','zhong':'中','fa':'發','bai':'白'
}

def analyze_defense(hand, p1, p2, p3):
    if not hand: return "請先輸入手牌"
    visible = hand + p1 + p2 + p3
    counts = collections.Counter(visible)
    discards = set(p1 + p2 + p3)
    
    # 筋牌 (Suji) 邏輯
    suji = set()
    for t in discards:
        if len(t) == 2 and t[1] in 'mts':
            v, s = int(t[0]), t[1]
            if v == 4: suji.update([f"1{s}", f"7{s}"])
            if v == 5: suji.update([f"2{s}", f"8{s}"])
            if v == 6: suji.update([f"3{s}", f"9{s}"])
            if v in [1, 7]: suji.add(f"4{s}")
            if v in [2, 8]: suji.add(f"5{s}")
            if v in [3, 9]: suji.add(f"6{s}")

    results = []
    for tile in set(hand):
        score, reason = 50, "普通牌"
        if tile in discards: score, reason = 100, "現物 (絕對安全)"
        elif tile in ["東","南","西","北","中","發","白"]:
            c = counts[tile]
            if c >= 3: score, reason = 90, "字牌場見 3+ (極安全)"
            elif c == 2: score, reason = 75, "字牌場見 2 (安全)"
            else: score, reason = 30, "生張字牌 (危險)"
        else:
            v, s = int(tile[0]), tile[1]
            if (v > 1 and counts.get(f"{v-1}{s}")==4) or (v < 9 and counts.get(f"{v+1}{s}")==4):
                score, reason = 85, "壁 (鄰牌已斷，安全)"
            elif tile in suji: score, reason = 70, "筋牌 (相對安全)"
            elif v in [1, 9]: score, reason = 60, "邊張 (較安全)"
        results.append({"牌": tile, "安全度": score, "理由": reason})
    return sorted(results, key=lambda x: x["安全度"], reverse=True)

# --- 2. 佈局與樣式 (完全對齊圖片 1) ---
st.set_page_config(page_title="麻將 AI 防守大師", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: nowrap !important; gap: 2px !important; }
    [data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; }
    div.stButton > button { background-color: #F0F0F0 !important; color: black !important; border: 1px solid black !important; border-radius: 0px !important; font-weight: bold !important; width: 100% !important; aspect-ratio: 1.1 / 1; font-size: clamp(8px, 2.5vw, 16px) !important; padding: 0px !important; }
    .mon-row { display: flex; border: 1px solid black; background-color: white; height: 35px; margin-top: -1px; }
    .mon-label { width: 50px; background-color: #D1F0FA; border-right: 1px solid black; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; color: black; flex-shrink: 0; }
    .mon-content { flex-grow: 1; display: flex; align-items: center; padding-left: 10px; font-weight: bold; color: black; font-size: 14px; }
    .ai-btn-style button { background-color: #00B050 !important; color: white !important; height: 80px !important; width: 80px !important; font-size: 18px !important; border: none !important; }
    .ai-res-box { flex-grow: 1; background-color: #D9EAD3; border: 1px dashed black; min-height: 120px; padding: 8px; color: black; font-size: 13px; overflow-y: auto; }
    [data-testid="stCameraInput"] { position: fixed; bottom: -1000px; } 
    </style>
    """, unsafe_allow_html=True)

# --- 3. 介面實作 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key not in ['last_selected', 'ai_res'] else ""

# A. 選牌區
def draw_row(labels, k):
    cols = st.columns(len(labels))
    for i, lb in enumerate(labels):
        if cols[i].button(lb, key=f"{k}_{i}"):
            st.session_state.last_selected = lb; st.rerun()

draw_row(["1m","2m","3m","4m","5m","6m","7m","8m","9m"], "m")
draw_row(["1s","2s","3s","4s","5s","6s","7s","8s","9s"], "s")
draw_row(["1t","2t","3t","4t","5t","6t","7t","8t","9t"], "t")
draw_row(["東","南","西","北","中","發","白"], "z")

# B. 指派動作
st.write("")
c_act = st.columns(4)
def add_t(target):
    if st.session_state.last_selected: target.append(st.session_state.last_selected); st.rerun()
if c_act[0].button("+我"): add_t(st.session_state.my_hand)
if c_act[1].button("+下"): add_t(st.session_state.p1_dis)
if c_act[2].button("+對"): add_t(st.session_state.p2_dis)
if c_act[3].button("+上"): add_t(st.session_state.p3_dis)

# C. 三家監視器
st.write("")
st.markdown(f'<div class="mon-row"><div class="mon-label">下家</div><div class="mon-content">{" ".join(st.session_state.p1_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mon-row"><div class="mon-label">對家</div><div class="mon-content">{" ".join(st.session_state.p2_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="mon-row"><div class="mon-label">上家</div><div class="mon-content">{" ".join(st.session_state.p3_dis)}</div></div>', unsafe_allow_html=True)

# D. 我的手牌區
st.markdown(f"### 我的手牌({len(st.session_state.my_hand)}/17)")
c_cam = st.columns([3, 1, 1])
with c_cam[2]: st.markdown('<label for="hidden-cam" style="cursor:pointer; background:#AAAAAA; padding:5px 10px; border:1px solid black; font-weight:bold; font-size:14px;">拍照</label>', unsafe_allow_html=True)
cap_img = st.camera_input("拍照", key="hidden-cam", label_visibility="collapsed")
if cap_img:
    file_bytes = np.asarray(bytearray(cap_img.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    cv2.imwrite("scan.jpg", img)
    result = CLIENT.infer("scan.jpg", model_id=MODEL_ID)
    if "predictions" in result:
        preds = result["predictions"]; preds.sort(key=lambda x: x["x"])
        st.session_state.my_hand = [TILE_MAP.get(p["class"], p["class"]) for p in preds]; st.rerun()

st.markdown(f'<div style="background:#EEE; border:1px solid black; min-height:50px; padding:5px; font-weight:bold; color:black;">{" ".join(st.session_state.my_hand)}</div>', unsafe_allow_html=True)
if st.button("🗑️ 清空手牌"): st.session_state.my_hand = []; st.rerun()

# E. AI 防守模擬區
st.divider()
ai_c1, ai_c2 = st.columns([1, 3])
with ai_c1:
    st.markdown('<div class="ai-btn-style">', unsafe_allow_html=True)
    if st.button("AI模擬"):
        st.session_state.ai_res = analyze_defense(st.session_state.my_hand, st.session_state.p1_dis, st.session_state.p2_dis, st.session_state.p3_dis)
    st.markdown('</div>', unsafe_allow_html=True)

with ai_c2:
    if isinstance(st.session_state.ai_res, list):
        txt = "".join([f"● <b>{i['牌']}</b>: 安全度 {i['安全度']}% ({i['理由']})<br>" for i in st.session_state.ai_res[:4]])
        st.markdown(f'<div class="ai-res-box"><b>🛡️ 防守分析建議：</b><br>{txt}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="ai-res-box">{st.session_state.ai_res if st.session_state.ai_res else "等待分析..."}</div>', unsafe_allow_html=True)
