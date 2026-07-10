import streamlit as st
import pandas as pd
import datetime
import io
import sqlite3
import openpyxl
import os

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

# --- 4. CSS 스타일 주입 (버튼 강제 2열 완벽 해결) ---
st.markdown("""
    <style>
        /* 앱 전체 가로 스크롤 방지 */
        .stApp, .block-container { overflow-x: hidden !important; max-width: 100vw !important; }
        
        /* ⭐️ 제목 1줄 고정 */
        @media (max-width: 768px) {
            h1 { white-space: nowrap !important; font-size: 5.5vw !important; letter-spacing: -0.5px !important; }
            h2 { white-space: nowrap !important; font-size: 4.5vw !important; letter-spacing: -0.5px !important; }
        }

        /* ⭐️ 표 1줄 고정 */
        .custom-overtime-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 15px; table-layout: fixed; }
        .custom-overtime-table th, .custom-overtime-table td { border: 1px solid #dcdde1; padding: 10px 2px; text-align: center !important; vertical-align: middle !important; }
        .custom-overtime-table th { background-color: #f0f2f6; color: #31333F; font-weight: bold; }
        .overtime-checked { background-color: #fff5f5; color: #ff4b4b; font-weight: bold; }
        
        @media (max-width: 768px) {
            .custom-overtime-table { font-size: 3vw !important; }
            .custom-overtime-table th, .custom-overtime-table td { 
                padding: 4px 0px !important; 
                height: 35px; 
                white-space: nowrap !important; 
                letter-spacing: -0.5px !important; 
            }
            .overtime-checked { font-size: 2.8vw !important; letter-spacing: -1px !important; }
        }

        /* ⭐️ 버튼 강제 2열 배치 (핵심 무적 CSS) */
        /* stVerticalBlock 안에 btn-grid라는 style 태그가 있으면 무조건 가로로 배치 */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
        
        /* 버튼이 들어있는 각각의 컨테이너를 정확히 반반(50%)으로 쪼갬 */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:not(:has(style)) {
            width: calc(50% - 4px) !important;
            flex: 0 0 calc(50% - 4px) !important;
            min-width: 0 !important; 
        }
        
        /* 스타일 태그가 들어있는 빈 공간은 화면에서 완전히 삭제 */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:has(style) {
            display: none !important;
        }
        
        /* 버튼 글씨 줄바꿈 방지 및 자동 축소 */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) button {
            white-space: nowrap !important;
            height: auto !important;
            min-height: 42px !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 5. 화면 레이아웃 분할 ---
col1, col2 = st.columns([1, 1.5])

# --- 왼쪽 영역: 야근 계획 등록/수정/취소 ---
with col1:
    st.header(f"📝 야근 계획 등록 ({today_str})")
    
    # ⭐️ 1. 이름 버튼 묶음 (컨테이너 사용으로 1줄 깨짐 방지)
    st.markdown("**1. 이름을 선택하세요**")
    with st.container():
        st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
        for name in members:
            btn_type = "primary" if name == st.session_state.selected_name else "secondary"
            if st.button(name, key=f"m_{name}", use_container_width=True, type=btn_type):
                st.session_state.selected_name = name
                st.rerun()
                
    st.write("") 
    
    # ⭐️ 2. 시간 버튼 묶음
    st.markdown("**2. 종료 시간을 선택하세요**")
    with st.container():
        st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
        for t_slot in time_slots:
            btn_type = "primary" if t_slot == st.session_state.selected_end_time else "secondary"
            if st.button(t_slot, key=f"t_{t_slot}", use_container_width=True, type=btn_type):
                st.session_state.selected_end_time = t_slot
                st.rerun()
                
    st.write("") 
    
    # ⭐️ 3. 등록/취소 버튼 묶음
    with st.container():
        st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
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

# --- 오른쪽 영역: 야근 현황판 및 맞춤형 엑셀 다운로드 ---
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
                
    html_code = f'<table class="custom-overtime-table"><thead><tr><th>시간</th>'
    for col in grid_df.columns: html_code += f'<th>{col}</th>'
    html_code += '</tr></thead><tbody>'
    for index, row in grid_df.iterrows():
        html_code += f'<tr><th>{index}</th>'
        for val in row:
            html_code += f'<td class="overtime-checked">{val}</td>' if val == "✔️ 야근" else f'<td>{val}</td>'
        html_code += '</tr>'
    html_code += '</tbody></table>'
    st.markdown(html_code, unsafe_allow_html=True)
    st.write("") 
    
    # ⭐️ 원본 엑셀 템플릿 파일 로드 및 데이터 입력 로직
    template_path = "template.xlsx"
    
    if os.path.exists(template_path):
        wb = openpyxl.load_workbook(template_path)
        ws = wb.active
        
        ws['F3'] = view_str
        
        start_row = 8
        for idx, (name, end_t) in enumerate(records, start=1):
            ws.cell(row=start_row, column=2, value=idx)                             
            ws.cell(row=start_row, column=3, value=name)                            
            ws.cell(row=start_row, column=5, value=f"17:30 ~ {end_t}")              
            ws.cell(row=start_row, column=6, value="업무 연장")                     
            start_row += 1
            
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        st.download_button(
            label=f"📥 {view_str} 양식 엑셀 다운로드",
            data=excel_buffer.getvalue(),
            file_name=f"야근계획서_{view_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.error("⚠️ 폴더 내에 'template.xlsx' 원본 양식 파일이 존재하지 않습니다. 깃허브에 양식 파일을 먼저 업로드해 주세요!")