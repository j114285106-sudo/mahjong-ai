import streamlit as st
import collections
import pandas as pd
import numpy as np
from inference_sdk import InferenceHTTPClient
import cv2

# --- 1. Roboflow 初始化 ---
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="cUeAQuPgQiWwm4oneikb"
)
MODEL_ID = "mahjong-vtacs/1"

TILE_MAP = {
    '1m':'一萬','2m':'二萬','3m':'三萬','4m':'四萬','5m':'五萬','6m':'六萬','7m':'七萬','8m':'八萬','9m':'九萬',
    '1s':'一條','2s':'二條','3s':'三條','4s':'四條','5s':'五條','6s':'六條','7s':'七條','8s':'八條','9s':'九條',
    '1t':'一筒','2t':'二筒','3t':'三筒','4t':'四筒','5t':'五筒','6t':'六筒','7t':'七筒','8t':'八筒','9t':'九筒',
    'east':'東','south':'南','west':'西','north':'北','zhong':'中','fa':'發','bai':'白'
}

# --- 2. 強力排版 CSS ---
st.set_page_config(page_title="麻將 AI 控制台", layout="centered")

st.markdown("""
    <style>
    /* 全域背景 */
    .stApp { background-color: #C1E6F3 !important; }
    header, footer, #MainMenu {visibility: hidden;}

    /* 【關鍵】強制手機版 columns 不換行 */
    [data-testid="column"] {
        flex: 1 1 0% !important; /* 強制所有列平均分配寬度 */
        min-width: 0px !important; /* 移除最小寬度限制 */
    }

    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important; /* 禁止換行 */
        align-items: center !important;
        gap: 2px !important;
    }

    /* 按鈕樣式：針對手機微調高度與間距 */
    div.stButton > button {
        background-color: #F0F0F0 !important;
        color: black !important;
        border: 2px solid black !important;
        border-radius: 0px !important;
        font-weight: bold !important;
        font-size: clamp(10px, 3vw, 16px) !important; /* 動態字體大小 */
        padding: 0px !important;
        width: 100% !important;
        height: 40px !important;
        line-height: 1 !important;
    }

    /* 監控條 */
    .monitor-box {
        background-color: white; border: 2px solid black; height: 40px;
        margin-bottom: 4px; display: flex; align-items: center; overflow: hidden;
    }
    .monitor-label {
        background-color: #D1F0FA; border-right: 2px solid black;
        width: 50px; height: 100%; display: flex; align-items: center;
        justify-content: center; font-weight: bold; font-size: 14px;
    }
    .monitor-content { padding-left: 8px; font-weight: bold; font-size: 16px; color: black; }

    /* AI 模擬大按鈕 */
    .ai-main-btn button { 
        background-color: #00B050 !important; color: white !important; 
        height: 80px !important; font-size: 18px !important; 
    }

    .hand-display {
        background-color: white; border: 2px solid black; min-height: 60px;
        margin-top: 5px; padding: 8px; font-size: 16px; font-weight: bold; color: black;
    }
    
    .ai-output {
        background-color: #D9EAD3; border: 2px dashed black;
        min-height: 80px; padding: 8px; color: black; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化 ---
if 'my_hand' not in st.session_state:
    for key in ['my_hand', 'p1_dis', 'p2_dis', 'p3_dis', 'last_selected', 'ai_res']:
        st.session_state[key] = [] if key not in ['last_selected', 'ai_res'] else ""

# --- 4. 界面布局 ---

st.markdown(f'<div class="monitor-box"><div class="monitor-label">下家</div><div class="monitor-content">{" ".join(st.session_state.p1_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="monitor-box"><div class="monitor-label">對家</div><div class="monitor-content">{" ".join(st.session_state.p2_dis)}</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="monitor-box"><div class="monitor-label">上家</div><div class="monitor-content">{" ".join(st.session_state.p3_dis)}</div></div>', unsafe_allow_html=True)

st.write("") 

# 強制九宮格排版
def tile_row(labels, row_key):
    cols = st.columns(len(labels))
    for i, label in enumerate(labels):
        if cols[i].button(label, key=f"sel_{row_key}_{i}"):
            st.session_state.last_selected = label
            st.rerun()

tile_row(["一萬","二萬","三萬","四萬","五萬","六萬","七萬","八萬","九萬"], "m")
tile_row(["一條","二條","三條","四條","五條","六條","七條","八條","九條"], "s")
tile_row(["一筒","二筒","三筒","四筒","五筒","六筒","七筒
