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

# --- 4. CSS 스타일 주입 (스트림릿 자바스크립트 명령 무력화 버전) ---
st.markdown("""
    <style>
        /* ⭐️ 전체 앱 가로 스크롤 원천 차단 */
        .stApp, .block-container {
            overflow-x: hidden !important;
            max-width: 100vw !important;
        }

        /* ⭐️ 모바일(768px 이하)에서 스트림릿이 강제로 1줄로 세우는 걸 온 힘을 다해 방어 */
        @media (max-width: 768px) {
            /* 버튼 두 개가 들어가는 가로 블록을 무조건 '반반 그리드'로 덮어쓰기 */
            div[data-testid="column"]:first-of-type div[data-testid="stHorizontalBlock"] {
                display: grid !important;
                grid-template-columns: repeat(2, 1fr) !important; /* 정확히 50%씩 반반 고정 */
                gap: 8px !important;
                width: 100% !important;
                flex-direction: row !important; /* 세로로 정렬하라는 스트림릿 명령 차단 */
                flex-wrap: nowrap !important;
            }
            
            /* 그리드 자식 요소(컬럼)들이 깨지지 않도록 강제 설정 */
            div[data-testid="column"]:first-of-type div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                flex: 1 1 0% !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            
            /* 버튼 글씨가 길어서 밖으로 튕겨 나가는 현상 방지 */
            div[data-testid="column"]:first-of-type button {
                width: 100% !important;
                white-space: normal !important;
                word-break: break-all !important;
                font-size: 13px !important;
                padding: 6px 4px !important;
            }
        }

        /* 표 반응형 스타일 */
        .custom-overtime-table {
            width: 100%;
            border-collapse: collapse;
            text-align: center;
            font-size: 15px;
            table-layout: fixed; 
        }
        .custom-overtime-table th, .custom-overtime-table td {
            border: 1px solid #dcdde1;
            padding: 10px 2px;
            text-align: center !important;
            vertical-align: middle !important;
        }
        .custom-overtime-table th { background-color: #f0f2f6; color: #31333F; font-weight: bold; }
        .overtime-checked { background-color: #fff5f5; color: #ff4b4b; font-weight: bold; }
        
        @media (max-width: 768px) {
            .custom-overtime-table { font-size: 11px !important; }
            .custom-overtime-table th, .custom-overtime-table td { 
                padding: 4px 0px !important; 
                height: 35px; 
                word-break: keep-all; 
            }
            .overtime-checked { font-size: 10px !important; letter-spacing: -1px; }
        }
    </style>
""", unsafe_allow_html=True)

# --- 5. 화면 레이아웃 분할 ---
col1, col2 = st.columns([1, 1.5])

# --- 왼쪽 영역: 야근 계획 등록/수정/취소 ---
with col1:
    st.header(f"📝 야근 계획 등록 ({today_str})")
    
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
    
    # 등록/취소 버튼
    btn_cols = st.columns(2)
    
    with btn_cols[0]:
        if st.button(f"🚀 {st.session_state.selected_name} 등록/수정", type="primary", use_container_width=True):
            conn = sqlite3.connect("overtime.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM overtime WHERE name=? AND date=?", (st.session_state.selected_name, today_str))
            record = cursor.fetchone()
            
            if record:
                cursor.execute("UPDATE overtime SET end_time=? WHERE id=?", (st.session_state.selected_end_time, record[0]))
                st.success(f"🔄 변경 완료!")
            else:
                cursor.execute("INSERT INTO overtime (name, date, end_time) VALUES (?, ?, ?)", 
                               (st.session_state.selected_name, today_str, st.session_state.selected_end_time))
                st.success(f"🎉 등록 완료!")
            
            conn.commit()
            conn.close()
            st.rerun()
            
    with btn_cols[1]:
        if st.button(f"🗑️ {st.session_state.selected_name} 취소", type="secondary", use_container_width=True):
            conn = sqlite3.connect("overtime.db")
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM overtime WHERE name=? AND date=?", (st.session_state.selected_name, today_str))
            
            if cursor.rowcount > 0:
                st.warning(f"🗑️ 취소 완료!")
            else:
                st.info(f"ℹ️ 기록 없음")
                
            conn.commit()
            conn.close()
            st.rerun()

# --- 오른쪽 영역: 야근 현황판 ---
with col2:
    view_date = st.date_input("🗓️ 과거 기록 조회", today_date)
    view_str = view_date.strftime('%Y-%m-%d')
    
    st.header(f"📊 야근 현황판 ({view_str})")
    
    grid_df = pd.DataFrame(index=time_slots, columns=members).fillna("")
    
    conn = sqlite3.connect("overtime.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, end_time FROM overtime WHERE date=?", (view_str,))
    records = cursor.fetchall()
    conn.close()
    
    for name, end_t in records:
        if end_t in grid_df.index and name in grid_df.columns:
            grid_df.loc[end_t, name] = "✔️ 야근"
                
    html_code = f'<table class="custom-overtime-table">'
    html_code += '<thead><tr><th>시간</th>'
    for col in grid_df.columns:
        html_code += f'<th>{col}</th>'
    html_code += '</tr></thead><tbody>'
    
    for index, row in grid_df.iterrows():
        html_code += f'<tr><th>{index}</th>'
        for val in row:
            if val == "✔️ 야근":
                html_code += f'<td class="overtime-checked">{val}</td>'
            else:
                html_code += f'<td>{val}</td>'
        html_code += '</tr>'
    html_code += '</tbody></table>'
    
    st.markdown(html_code, unsafe_allow_html=True)
    st.write("") 
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        grid_df.to_excel(writer, sheet_name='야근계획', index=True)
    
    st.download_button(
        label=f"📥 {view_str} 현황 다운로드",
        data=excel_buffer.getvalue(),
        file_name=f"야근계획_{view_str}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )