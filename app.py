import streamlit as st
import pandas as pd
import datetime
import io
import sqlite3

# 1. 페이지 설정
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.title("🌙 야근 계획 관리 시스템")

# 2. 데이터 정의
members = ["권회준", "김민호", "오진영", "강한수", "최지훈", "박현수", "테이"]
time_slots = ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]
today_date = datetime.date.today()
today_str = today_date.strftime('%Y-%m-%d')

# 3. [에러 수정] 함수를 확실하게 정의
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

# 이제 함수가 정의된 후 호출하므로 NameError가 나지 않습니다!
init_db()

# 4. 상태 관리
if "selected_name" not in st.session_state:
    st.session_state.selected_name = members[0]
if "selected_end_time" not in st.session_state:
    st.session_state.selected_end_time = time_slots[0]

# 5. CSS 스타일 주입 (모바일 가로 스크롤 방지 및 2열 고정)
st.markdown("""
    <style>
        .stApp { overflow-x: hidden !important; }
        .grid-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 16px;
        }
        .custom-overtime-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 14px; table-layout: fixed; }
        .custom-overtime-table th, .custom-overtime-table td { border: 1px solid #dcdde1; padding: 6px 1px; }
        .custom-overtime-table th { background-color: #f0f2f6; }
        .overtime-checked { background-color: #fff5f5; color: #ff4b4b; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 6. 버튼 렌더링 함수
def render_grid_buttons(label, options, selected_key):
    st.markdown(f"**{label}**")
    st.markdown('<div class="grid-container">', unsafe_allow_html=True)
    for opt in options:
        btn_type = "primary" if opt == st.session_state[selected_key] else "secondary"
        if st.button(opt, key=f"{selected_key}_{opt}", use_container_width=True, type=btn_type):
            st.session_state[selected_key] = opt
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 7. 메인 화면 배치
col1, col2 = st.columns([1, 1.5])

with col1:
    render_grid_buttons("1. 이름을 선택하세요", members, "selected_name")
    render_grid_buttons("2. 종료 시간을 선택하세요", time_slots, "selected_end_time")
    
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("🚀 등록/수정", type="primary", use_container_width=True):
        conn = sqlite3.connect("overtime.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM overtime WHERE name=? AND date=?", (st.session_state.selected_name, today_str))
        if cursor.fetchone():
            cursor.execute("UPDATE overtime SET end_time=? WHERE name=? AND date=?", (st.session_state.selected_end_time, st.session_state.selected_name, today_str))
        else:
            cursor.execute("INSERT INTO overtime (name, date, end_time) VALUES (?, ?, ?)", (st.session_state.selected_name, today_str, st.session_state.selected_end_time))
        conn.commit()
        conn.close()
        st.rerun()
        
    if btn_col2.button("🗑️ 취소", type="secondary", use_container_width=True):
        conn = sqlite3.connect("overtime.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM overtime WHERE name=? AND date=?", (st.session_state.selected_name, today_str))
        conn.commit()
        conn.close()
        st.rerun()

with col2:
    view_date = st.date_input("🗓️ 과거 기록 조회", today_date)
    view_str = view_date.strftime('%Y-%m-%d')
    st.header(f"📊 현황 ({view_str})")
    
    grid_df = pd.DataFrame(index=time_slots, columns=members).fillna("")
    conn = sqlite3.connect("overtime.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, end_time FROM overtime WHERE date=?", (view_str,))
    for name, end_t in cursor.fetchall():
        if end_t in grid_df.index and name in grid_df.columns:
            grid_df.loc[end_t, name] = "✔️"
    conn.close()
    
    html = '<table class="custom-overtime-table"><thead><tr><th>시간</th>' + ''.join([f'<th>{c}</th>' for c in members]) + '</tr></thead><tbody>'
    for idx, row in grid_df.iterrows():
        html += f'<tr><th>{idx}</th>' + ''.join([f'<td class="{"overtime-checked" if val else ""}">{val}</td>' for val in row]) + '</tr>'
    st.markdown(html + '</tbody></table>', unsafe_allow_html=True)
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer: grid_df.to_excel(writer, sheet_name='야근계획')
    st.download_button("📥 엑셀 다운로드", data=buf.getvalue(), file_name=f"야근계획_{view_str}.xlsx")