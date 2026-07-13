import streamlit as st
import pandas as pd
import datetime
import io
import openpyxl
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# 모바일/PC 넓게 쓰기 설정
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.title("🌙 야근 계획 관리 시스템")

# --- 1. 고정 데이터 정의 ---
members = ["권회준", "김민호", "오진영", "강한수", "최지훈", "박현수", "테이"]
time_slots = ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]

today_date = datetime.date.today()
today_str = today_date.strftime('%Y-%m-%d')

# --- 2. 구글 스프레드시트 연동 (DB 대체) ---
@st.cache_resource
def init_connection():
    # 스트림릿 Secrets에 저장해둔 JSON 문자열을 불러옴
    key_dict = json.loads(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1v4REfMtoTB9CQzBRks45UpaVmptHxYD-mYeAOnavDvY/edit?gid=0#gid=0"

    # 공유받은 구글 시트의 첫 번째 워크시트를 불러옴
    return client.open_by_url(sheet_url).sheet1

# 시트 연결
sheet = init_connection()

# --- 3. 상태 관리 ---
if "selected_name" not in st.session_state:
    st.session_state.selected_name = members[0]
if "selected_end_time" not in st.session_state:
    st.session_state.selected_end_time = time_slots[0]

# --- 4. CSS 스타일 주입 (디자인 유지) ---
st.markdown("""
    <style>
        .stApp, .block-container { overflow-x: hidden !important; max-width: 100vw !important; }
        
        @media (max-width: 768px) {
            h1 { white-space: nowrap !important; font-size: 5.5vw !important; letter-spacing: -0.5px !important; }
            h2 { white-space: nowrap !important; font-size: 4.5vw !important; letter-spacing: -0.5px !important; }
        }

        .custom-overtime-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 15px; table-layout: fixed; }
        .custom-overtime-table th, .custom-overtime-table td { border: 1px solid #dcdde1; padding: 10px 2px; text-align: center !important; vertical-align: middle !important; }
        .custom-overtime-table th { background-color: #f0f2f6; color: #31333F; font-weight: bold; }
        .overtime-checked { background-color: #fff5f5; color: #ff4b4b; font-weight: bold; }
        
        @media (max-width: 768px) {
            .custom-overtime-table { font-size: 3vw !important; }
            .custom-overtime-table th, .custom-overtime-table td { padding: 4px 0px !important; height: 35px; white-space: nowrap !important; letter-spacing: -0.5px !important; }
            .overtime-checked { font-size: 2.8vw !important; letter-spacing: -1px !important; }
        }

        /* ⭐️ 버튼 강제 2열 배치 */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) {
            display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 8px !important;
        }
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:not(:has(style)) {
            width: calc(50% - 4px) !important; flex: 0 0 calc(50% - 4px) !important; min-width: 0 !important; 
        }
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:has(style) {
            display: none !important;
        }
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) button {
            white-space: nowrap !important; height: auto !important; min-height: 42px !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 5. 화면 레이아웃 분할 ---
col1, col2 = st.columns([1, 1.5])

# --- 왼쪽 영역: 야근 계획 등록/수정/취소 ---
with col1:
    st.header(f"📝 야근 계획 등록 ({today_str})")
    
    st.markdown("**1. 이름을 선택하세요**")
    with st.container():
        st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
        for name in members:
            btn_type = "primary" if name == st.session_state.selected_name else "secondary"
            if st.button(name, key=f"m_{name}", use_container_width=True, type=btn_type):
                st.session_state.selected_name = name
                st.rerun()
                
    st.write("") 
    
    st.markdown("**2. 종료 시간을 선택하세요**")
    with st.container():
        st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
        for t_slot in time_slots:
            btn_type = "primary" if t_slot == st.session_state.selected_end_time else "secondary"
            if st.button(t_slot, key=f"t_{t_slot}", use_container_width=True, type=btn_type):
                st.session_state.selected_end_time = t_slot
                st.rerun()
                
    st.write("") 
    
    # 등록/취소 버튼 묶음 (구글 시트 연동)
    with st.container():
        st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
        
        if st.button(f"🚀 {st.session_state.selected_name} 등록/수정", type="primary", use_container_width=True):
            all_data = sheet.get_all_values()
            row_to_update = -1
            
            # 기존에 등록한 내역이 있는지 확인
            for i, row in enumerate(all_data):
                if i > 0 and len(row) >= 4 and row[1] == st.session_state.selected_name and row[2] == today_str:
                    row_to_update = i + 1 # gspread는 1번 인덱스부터 시작
                    break
                    
            if row_to_update != -1:
                sheet.update_cell(row_to_update, 4, st.session_state.selected_end_time) # 4번째 열(end_time) 수정
                st.success(f"🔄 변경 완료!")
            else:
                new_id = len(all_data)
                sheet.append_row([new_id, st.session_state.selected_name, today_str, st.session_state.selected_end_time])
                st.success(f"🎉 등록 완료!")
            st.rerun()
            
        if st.button(f"🗑️ {st.session_state.selected_name} 취소", type="secondary", use_container_width=True):
            all_data = sheet.get_all_values()
            row_to_delete = -1
            
            # 삭제할 내역 찾기
            for i, row in enumerate(all_data):
                if i > 0 and len(row) >= 4 and row[1] == st.session_state.selected_name and row[2] == today_str:
                    row_to_delete = i + 1
                    break
                    
            if row_to_delete != -1:
                sheet.delete_rows(row_to_delete)
                st.warning(f"🗑️ 취소 완료!")
            else:
                st.info(f"ℹ️ 기록 없음")
            st.rerun()

# --- 오른쪽 영역: 야근 현황판 및 맞춤형 엑셀 다운로드 ---
with col2:
    view_date = st.date_input("🗓️ 과거 기록 조회", today_date)
    view_str = view_date.strftime('%Y-%m-%d')
    
    st.header(f"📊 야근 현황판 ({view_str})")
    
    grid_df = pd.DataFrame(index=time_slots, columns=members).fillna("")
    
    # 구글 시트에서 해당 날짜 데이터만 필터링해서 가져오기
    all_data = sheet.get_all_values()
    records = []
    for row in all_data[1:]: # 첫 번째 헤더 줄 제외
        if len(row) >= 4 and row[2] == view_str:
            records.append((row[1], row[3])) # 이름, 종료시간
    
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