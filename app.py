import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import io
import openpyxl
import os
import json
import gspread
from google.oauth2.service_account import Credentials

hide_profile_and_logo_style = """
<style>
/* 1. 우측 상단 툴바 전체(프로필 아이콘, 스트림릿 로고 포함) 숨기기 */
[data-testid="stToolbar"] {
    display: none !important;
}

/* 2. 'Deploy' 또는 앱 상태를 나타내는 버튼/위젯 숨기기 */
[data-testid="stAppDeployButton"], 
[data-testid="stStatusWidget"] {
    display: none !important;
}

/* 3. 헤더 영역의 색상 띠(Decoration) 숨기기 (선택 사항) */
[data-testid="stDecoration"] {
    display: none !important;
}
</style>
"""
st.markdown(hide_profile_and_logo_style, unsafe_allow_html=True)

# 모바일/PC 넓게 쓰기 설정
st.set_page_config(
    page_title="T/S 야근 관리",       
    page_icon="🏢",                 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

st.title("🏢 T/S 야근 계획 관리 시스템")
st.caption("✨ Created by tskwon")

# --- 1. 고정 데이터 정의 ---
members = ["권회준", "김민호", "오진영", "강한수", "최지훈", "박현수", "테이"]
time_slots = ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]

# KST(UTC+9) 타임존을 적용하여 정확한 한국 시간 계산
KST = timezone(timedelta(hours=9))
today_date = datetime.now(KST).date()
today_str = today_date.strftime('%Y-%m-%d')

# --- 2. 구글 스프레드시트 연동 ---
@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1v4REfMtoTB9CQzBRks45UpaVmptHxYD-mYeAOnavDvY/edit?gid=0#gid=0"

    return client.open_by_url(sheet_url).sheet1

sheet = init_connection()

# --- 3. 상태 관리 ---
if "selected_name" not in st.session_state:
    st.session_state.selected_name = members[0]
if "selected_end_time" not in st.session_state:
    st.session_state.selected_end_time = time_slots[0]
if "reason_input" not in st.session_state:
    st.session_state.reason_input = ""

# --- 4. CSS 스타일 주입 ---
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
        
        /* 주간 현황 테이블 스타일 */
        .weekly-summary-table { width: 100%; text-align: center; font-size: 14px; margin-top: 10px; border-collapse: collapse;}
        .weekly-summary-table th, .weekly-summary-table td { border: 1px solid #dcdde1; padding: 8px; }
        .weekly-summary-table th { background-color: #e8f0fe; color: #1a73e8; }
        .weekly-hours { font-weight: bold; color: #2c3e50; }
        .weekly-label { font-weight: bold; background-color: #f8f9fa; color: #31333F; }
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

    st.markdown("**3. 근무 사유를 입력하세요 (필수)**")
    st.text_input("사유 입력란", key="reason_input", label_visibility="collapsed", placeholder="예: B/T 3건 및 견뢰도 Test (미입력 시 등록 불가)")
    
    st.write("") 

    # 등록/취소 버튼 묶음 
    with st.container():
        st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
        
        if st.button(f"🚀 {st.session_state.selected_name} 등록/수정", type="primary", use_container_width=True):
            if not st.session_state.reason_input.strip():
                st.error("⚠️ 근무 사유를 반드시 적어주세요!")
            else:
                all_data = sheet.get_all_values()
                row_to_update = -1
                
                for i, row in enumerate(all_data):
                    if i > 0 and len(row) >= 4 and row[1] == st.session_state.selected_name and row[2] == today_str:
                        row_to_update = i + 1 
                        break
                        
                if row_to_update != -1:
                    sheet.update_cell(row_to_update, 4, st.session_state.selected_end_time) 
                    sheet.update_cell(row_to_update, 5, st.session_state.reason_input)
                    st.success(f"🔄 변경 완료!")
                else:
                    new_id = len(all_data)
                    sheet.append_row([new_id, st.session_state.selected_name, today_str, st.session_state.selected_end_time, st.session_state.reason_input])
                    st.success(f"🎉 등록 완료!")
                
                st.rerun()
            
        if st.button(f"🗑️ {st.session_state.selected_name} 취소", type="secondary", use_container_width=True):
            all_data = sheet.get_all_values()
            row_to_delete = -1
            
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

# --- 오른쪽 영역: 탭(Tab) 기반 야근 현황판 ---
with col2:
    # ⭐️ 기준 날짜 선택 (이 날짜를 기준으로 현황판과 주간 누적이 모두 변경됨)
    view_date = st.date_input("🗓️ 조회 기준 날짜 선택", today_date)
    view_str = view_date.strftime('%Y-%m-%d')
    
    # ⭐️ 탭(Tab) 생성
    tab1, tab2 = st.tabs(["📊 일간 현황", "⏱️ 주간 누적 (최근 8주)"])
    
    # 구글 시트에서 전체 데이터 한 번만 로드 (탭 공유용)
    all_data = sheet.get_all_values()
    
    # === 탭 1: 일간 야근 현황 ===
    with tab1:
        st.header(f"📊 야근 현황판 ({view_str})")
        grid_df = pd.DataFrame(index=time_slots, columns=members).fillna("")
        records = []
        
        # 해당 날짜 기록 필터링
        for row in all_data[1:]:
            if len(row) >= 4 and row[2] == view_str:
                row_name = row[1]
                row_end_time = row[3]
                reason = row[4] if len(row) >= 5 and row[4].strip() != "" else "업무 연장"
                records.append((row_name, row_end_time, reason))
        
        # 테이블 표기
        for name, end_t, reason in records:
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
        
        # 엑셀 다운로드 (일간 기준)
        template_path = "template.xlsx"
        if os.path.exists(template_path):
            wb = openpyxl.load_workbook(template_path)
            ws = wb.active
            ws['F3'] = view_str
            
            start_row = 8
            for idx, (name, end_t, reason) in enumerate(records, start=1):
                ws.cell(row=start_row, column=2, value=idx)                             
                ws.cell(row=start_row, column=3, value=name)                            
                ws.cell(row=start_row, column=5, value=f"17:30 ~ {end_t}")              
                ws.cell(row=start_row, column=6, value=reason)                      
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

    # === 탭 2: 주간 누적 8주 현황 ===
    with tab2:
        # 선택한 날짜가 속한 주의 월요일
        current_week_start = view_date - timedelta(days=view_date.weekday())
        
        # 과거 8주 차 날짜 범위 계산 (오래된 주 -> 현재 주 순서로 나열)
        weeks_info = []
        for i in range(7, -1, -1):
            w_start = current_week_start - timedelta(weeks=i)
            w_end = w_start + timedelta(days=6)
            label = f"{w_start.strftime('%m/%d')} ~ {w_end.strftime('%m/%d')}"
            weeks_info.append({"start": w_start, "end": w_end, "label": label})
            
        # 데이터를 담을 딕셔너리 초기화
        weekly_data = { w["label"]: { m: 0.0 for m in members } for w in weeks_info }
        
        def calculate_overtime_hours(end_time_str):
            try:
                start = datetime.strptime("17:30", "%H:%M")
                end = datetime.strptime(end_time_str, "%H:%M")
                return (end - start).total_seconds() / 3600.0
            except ValueError:
                return 0.0

        # 구글 시트 전체 기록에서 8주 이내 데이터 필터링하여 합산
        for row in all_data[1:]: 
            if len(row) >= 4:
                try:
                    row_date = datetime.strptime(row[2], "%Y-%m-%d").date()
                    row_name = row[1]
                    row_end_time = row[3]
                    
                    # 8주의 처음과 끝 사이에 포함되는지 먼저 확인
                    if weeks_info[0]["start"] <= row_date <= weeks_info[-1]["end"] and row_name in members:
                        # 어느 주차에 속하는지 찾아 누적합
                        for w in weeks_info:
                            if w["start"] <= row_date <= w["end"]:
                                weekly_data[w["label"]][row_name] += calculate_overtime_hours(row_end_time)
                                break
                except ValueError:
                    continue
        
        # 8주 현황 렌더링
        st.subheader("⏱️ 최근 8주 누적 야근 시간")
        
        weekly_html = '<table class="weekly-summary-table"><thead><tr><th>주차 (기간)</th>'
        for member in members:
            weekly_html += f'<th>{member}</th>'
        weekly_html += '</tr></thead><tbody>'
        
        # 주차별 행 추가
        for w in weeks_info:
            label = w["label"]
            weekly_html += f'<tr><td class="weekly-label">{label}</td>'
            for member in members:
                hours = weekly_data[label][member]
                display_text = f"{hours:.1f}h" if hours > 0 else "-"
                weekly_html += f'<td class="weekly-hours">{display_text}</td>'
            weekly_html += '</tr>'
            
        weekly_html += '</tbody></table>'
        st.markdown(weekly_html, unsafe_allow_html=True)