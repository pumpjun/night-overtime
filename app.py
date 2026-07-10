import streamlit as st
import pandas as pd
import datetime
import io
import sqlite3

# 모바일/PC 넓게 쓰기 설정
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.title("🌙 야근 계획 관리 시스템")

# --- 1. 고정 데이터 정의 ---
members = ["권회준", "김민호", "오진영", "강한수", "최지훈", "박현수", "테이"]
time_slots = ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]

today_date = datetime.date.today()
today_str = today_date.strftime('%Y-%m-%d')

# --- 2. DB 초기화 ---
def init_db():
    conn = sqlite3.connect("overtime.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS overtime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT,
            end_time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- 3. 상태 관리 ---
if "selected_name" not in st.session_state:
    st.session_state.selected_name = members[0]
if "selected_end_time" not in st.session_state:
    st.session_state.selected_end_time = time_slots[0]

# --- 4. CSS 스타일 주입 (화면 탈출 완벽 방어) ---
st.markdown("""
    <style>
        /* ⭐️ 1. 전체 앱 가로 스크롤 금지 */
        .stApp, .block-container {
            overflow-x: hidden !important;
            width: 100% !important;
        }

        /* ⭐️ 2. 버튼이 화면 밖으로 튀어나가지 않게 강제 축소 */
        @media (max-width: 768px) {
            div[data-testid="column"]:first-of-type div[data-testid="stHorizontalBlock"] {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: wrap !important;
                gap: 4px !important;
            }
            div[data-testid="column"]:first-of-type div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                width: calc(50% - 4px) !important;
                flex: 1 1 calc(50% - 4px) !important;
                min-width: 0 !important; /* ⭐️ 핵심: 최소 너비 제한 해제 */
                max-width: 50% !important;
            }
            /* 버튼 글자 크기 강제 축소 */
            div[data-testid="column"]:first-of-type button {
                font-size: 12px !important;
                padding: 4px 2px !important;
            }
        }

        /* 표 반응형 */
        .custom-overtime-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 14px; table-layout: fixed; }
        .custom-overtime-table th, .custom-overtime-table td { border: 1px solid #dcdde1; padding: 6px 1px; }
        .custom-overtime-table th { background-color: #f0f2f6; font-weight: bold; }
        .overtime-checked { background-color: #fff5f5; color: #ff4b4b; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 5. 화면 레이아웃 분할 ---
col1, col2 = st.columns([1, 1.5])

# --- 왼쪽 영역: 야근 계획 등록/수정/취소 ---
with col1:
    st.header(f"📝 야근 계획 등록")
    
    st.markdown("**1. 이름을 선택하세요**")
    for i in range(0, len(members), 2):
        row_cols = st.columns(2)
        if i < len(members):
            name = members[i]
            btn_type = "primary" if name == st.session_state.selected_name else "secondary"
            if row_cols[0].button(name, key=f"m_{name}", use_container_width=True, type=btn_type):
                st.session_state.selected_name = name
                st.rerun()
        if i + 1 < len(members):
            name = members[i+1]
            btn_type = "primary" if name == st.session_state.selected_name else "secondary"
            if row_cols[1].button(name, key=f"m_{name}", use_container_width=True, type=btn_type):
                st.session_state.selected_name = name
                st.rerun()
            
    st.write("") 
    
    st.markdown("**2. 종료 시간을 선택하세요**")
    for i in range(0, len(time_slots), 2):
        row_cols = st.columns(2)
        if i < len(time_slots):
            t_slot = time_slots[i]
            btn_type = "primary" if t_slot == st.session_state.selected_end_time else "secondary"
            if row_cols[0].button(t_slot, key=f"t_{t_slot}", use_container_width=True, type=btn_type):
                st.session_state.selected_end_time = t_slot
                st.rerun()
        if i + 1 < len(time_slots):
            t_slot = time_slots[i+1]
            btn_type = "primary" if t_slot == st.session_state.selected_end_time else "secondary"
            if row_cols[1].button(t_slot, key=f"t_{t_slot}", use_container_width=True, type=btn_type):
                st.session_state.selected_end_time = t_slot
                st.rerun()
            
    st.write("") 
    
    btn_cols = st.columns(2)
    with btn_cols[0]:
        if st.button(f"🚀 등록/수정", type="primary", use_container_width=True):
            conn = sqlite3.connect("overtime.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM overtime WHERE name=? AND date=?", (st.session_state.selected_name, today_str))
            record = cursor.fetchone()
            if record:
                cursor.execute("UPDATE overtime SET end_time=? WHERE id=?", (st.session_state.selected_end_time, record[0]))
            else:
                cursor.execute("INSERT INTO overtime (name, date, end_time) VALUES (?, ?, ?)", 
                               (st.session_state.selected_name, today_str, st.session_state.selected_end_time))
            conn.commit()
            conn.close()
            st.rerun()
    with btn_cols[1]:
        if st.button(f"🗑️ 취소", type="secondary", use_container_width=True):
            conn = sqlite3.connect("overtime.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM overtime WHERE name=? AND date=?", (st.session_state.selected_name, today_str))
            conn.commit()
            conn.close()
            st.rerun()

# --- 오른쪽 영역: 야근 현황판 ---
with col2:
    view_date = st.date_input("🗓️ 과거 기록 조회", today_date)
    view_str = view_date.strftime('%Y-%m-%d')
    st.header(f"📊 현황 ({view_str})")
    
    grid_df = pd.DataFrame(index=time_slots, columns=members).fillna("")
    conn = sqlite3.connect("overtime.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, end_time FROM overtime WHERE date=?", (view_str,))
    records = cursor.fetchall()
    conn.close()
    
    for name, end_t in records:
        if end_t in grid_df.index and name in grid_df.columns:
            grid_df.loc[end_t, name] = "✔️"
                
    html_code = f'<table class="custom-overtime-table">'
    html_code += '<thead><tr><th>시간</th>'
    for col in grid_df.columns:
        html_code += f'<th>{col}</th>'
    html_code += '</tr></thead><tbody>'
    for index, row in grid_df.iterrows():
        html_code += f'<tr><th>{index}</th>'
        for val in row:
            html_code += f'<td class="{"overtime-checked" if val else ""}">{val}</td>'
        html_code += '</tr>'
    html_code += '</tbody></table>'
    st.markdown(html_code, unsafe_allow_html=True)
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        grid_df.to_excel(writer, sheet_name='야근계획', index=True)
    st.download_button("📥 엑셀 다운로드", data=excel_buffer.getvalue(), file_name=f"야근계획_{view_str}.xlsx")