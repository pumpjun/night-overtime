import streamlit as st
import pandas as pd
import datetime
import io
import sqlite3

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.title("🌙 야근 계획 관리 시스템")

# ... (기존 데이터 정의 및 DB 초기화 함수는 동일) ...
members = ["권회준", "김민호", "오진영", "강한수", "최지훈", "박현수", "테이"]
time_slots = ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]
today_date = datetime.date.today()
today_str = today_date.strftime('%Y-%m-%d')
init_db() # 함수가 정의되어 있다고 가정

# --- CSS: 2열 강제 고정 (핵심) ---
st.markdown("""
    <style>
        /* 버튼을 담은 컨테이너를 가로 2열 그리드로 강제 변환 */
        .grid-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

# --- 버튼 렌더링 함수 (st.columns 대신 div.grid-container 활용) ---
def render_grid_buttons(label, options, selected_key):
    st.markdown(f"**{label}**")
    # HTML로 직접 div 구조를 만들어 스트림릿 엔진의 방해를 피함
    st.markdown('<div class="grid-container">', unsafe_allow_html=True)
    
    # 2열을 위한 버튼들 수동 배치
    for i in range(0, len(options), 2):
        row = st.columns(2)
        for j in range(2):
            if i + j < len(options):
                opt = options[i+j]
                # 버튼을 클릭하면 세션 상태 업데이트
                btn_type = "primary" if opt == st.session_state[selected_key] else "secondary"
                if row[j].button(opt, key=f"{selected_key}_{opt}", use_container_width=True, type=btn_type):
                    st.session_state[selected_key] = opt
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 메인 실행 ---
with st.columns([1, 1.5])[0]:
    render_grid_buttons("1. 이름을 선택하세요", members, "selected_name")
    render_grid_buttons("2. 종료 시간을 선택하세요", time_slots, "selected_end_time")
    
    # 등록/취소는 동일하게 유지...