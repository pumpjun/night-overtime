import streamlit as st
import pandas as pd
import datetime
import io
import sqlite3

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.title("🌙 야근 계획 관리 시스템")

# [init_db 및 데이터 정의는 이전과 동일]
members = ["권회준", "김민호", "오진영", "강한수", "최지훈", "박현수", "테이"]
time_slots = ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]
today_date = datetime.date.today()
today_str = today_date.strftime('%Y-%m-%d')

def init_db():
    conn = sqlite3.connect("overtime.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS overtime (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, date TEXT, end_time TEXT)")
    conn.commit()
    conn.close()
init_db()

# --- CSS: 2열 강제 고정 (중요) ---
st.markdown("""
    <style>
        .grid-container {
            display: grid;
            grid-template-columns: 1fr 1fr; /* 무조건 가로 2등분 */
            gap: 8px;
            width: 100%;
        }
        /* 버튼이 꽉 차게 */
        div.stButton > button {
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

# --- 새로운 버튼 렌더링 함수 ---
def render_grid_buttons(label, options, selected_key):
    st.markdown(f"**{label}**")
    st.markdown('<div class="grid-container">', unsafe_allow_html=True)
    for opt in options:
        # st.button 대신 HTML/CSS 영역 안에 배치
        btn_type = "primary" if opt == st.session_state.get(selected_key) else "secondary"
        if st.button(opt, key=f"{selected_key}_{opt}", type=btn_type):
            st.session_state[selected_key] = opt
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 초기화
if "selected_name" not in st.session_state: st.session_state.selected_name = members[0]
if "selected_end_time" not in st.session_state: st.session_state.selected_end_time = time_slots[0]

# [이하 현황판 로직은 동일]