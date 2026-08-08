import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta, timezone
import json
import gspread
from google.oauth2.service_account import Credentials
import random
import time

# ⭐️ 1. 모바일/PC 넓게 쓰기 설정 (st.set_page_config는 항상 최상단에 위치해야 합니다)
st.set_page_config(
    page_title="T/S 근무 관리",       
    page_icon="🗓️", # 💡 브라우저 탭 이모티콘 (원하는 이모티콘으로 변경 가능)
    layout="wide", 
    initial_sidebar_state="collapsed" 
)

# ⭐️ 2. 사용자 및 관리자 정의
members = ["권회준", "김민호", "오진영", "강한수", "최지훈", "박현수", "테이"]
admins = ["장현준", "김동기", "최상철", "강택규", "김현준"]

ALL_USERS = members + admins
HOLIDAY_USERS = admins + members 

# ⭐️ 3. 구글 스프레드시트 연동
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
    doc = client.open_by_url(sheet_url)
    return doc

# 문서 및 시트 연동
doc = init_connection()
sheet = doc.sheet1                       # 기존: 근무기록 시트
account_sheet = doc.worksheet("계정정보")  # 신규: 계정/비밀번호 시트 (구글 시트에 미리 만들어두어야 함)

# 데이터 가져오기
all_data = sheet.get_all_values()
account_data = account_sheet.get_all_values()

# 로그인 화면보다 위에서 USER_PINS를 미리 만들어 둡니다!
USER_PINS = {row[0]: row[1] for row in account_data[1:] if len(row) >= 2}

def get_work_type(row):
    if len(row) >= 6 and row[5].strip() != "":
        return row[5].strip()
    if len(row) >= 4 and row[3] in ["12:00", "17:00"]:
        return "휴일"
    return "야간"


# ⭐️ 4. CSS 스타일 전역 주입
custom_css = """
<style>
    /* 1. 기본 UI 요소 및 상단 헤더 완전 숨기기 */
    [data-testid="stToolbar"], [data-testid="stAppDeployButton"], 
    [data-testid="stStatusWidget"], [data-testid="stDecoration"], 
    [data-testid="collapsedControl"], header[data-testid="stHeader"] { 
        display: none !important; 
    }
    
    /* 2. 전체 스크롤바 투명하게 숨기기 */
    ::-webkit-scrollbar { width: 0px; height: 0px; background: transparent; }
    html, body { -ms-overflow-style: none; scrollbar-width: none; overflow-x: hidden; }
    
    /* 3. 위아래 여백 대폭 축소 (1rem으로 최소화) */
    .stApp, .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 1rem !important; 
        max-width: 100vw !important; 
    }
    
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        h1, h2, h3 {
            white-space: normal !important;
            word-break: keep-all !important;
            font-size: 6vw !important;
            letter-spacing: -0.5px !important;
        }
    }
    
    /* 탭(Tab) 아래 여백 축소 */
    .stTabs [data-baseweb="tab-panel"] { padding-top: 0.5rem !important; }
    
    /* 테이블 디자인 */
    .custom-overtime-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 14.5px; table-layout: fixed; }
    .custom-overtime-table th, .custom-overtime-table td { border: 1px solid #dcdde1; padding: 6px 2px; text-align: center !important; vertical-align: middle !important; }
    .custom-overtime-table th { background-color: #f0f2f6; color: #31333F; font-weight: bold; }
    .overtime-checked { background-color: #fff5f5; color: #ff4b4b; font-weight: bold; }
    
    @media (max-width: 768px) {
        .custom-overtime-table { font-size: 2.8vw !important; }
        .custom-overtime-table th, .custom-overtime-table td { padding: 4px 0px !important; height: 30px; white-space: nowrap !important; letter-spacing: -0.5px !important; }
        .overtime-checked { font-size: 2.6vw !important; letter-spacing: -1px !important; }
    }
    
    /* 버튼 2열 그리드 배치 */
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) {
        display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 6px !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:not(:has(style)) {
        width: calc(50% - 3px) !important; flex: 0 0 calc(50% - 3px) !important; min-width: 0 !important; 
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:has(style) {
        display: none !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) button {
        white-space: nowrap !important; height: auto !important; min-height: 38px !important; padding: 0 !important;
    }
    
    /* 8주 달력 테이블 스타일 */
    .weekly-summary-table { width: 100%; text-align: center; font-size: 13.5px; margin-top: 5px; border-collapse: collapse; table-layout: fixed; }
    .weekly-summary-table th, .weekly-summary-table td { border: 1px solid #dcdde1; padding: 6px 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .weekly-summary-table th { background-color: #e8f0fe; color: #1a73e8; }
    .weekly-hours { font-weight: bold; color: #2c3e50; background-color: #f1f3f5; }
    .weekly-label { font-weight: bold; background-color: #f8f9fa; color: #31333F; }
    
    @media (max-width: 768px) {
        .weekly-summary-table { font-size: 2.3vw !important; }
        .weekly-summary-table th, .weekly-summary-table td { padding: 3px 1px !important; }
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ⭐️ 매일 바뀌는 일일 예외 암호 생성 함수
def get_daily_password(date_str):
    random.seed(date_str + "_TS_TEAM_SECRET")
    pw = str(random.randint(1000, 9999))
    random.seed() 
    return pw


# ⭐️ 하이웍스 최적화 폰트 사이즈 반영 및 과거기록 HR 자동계산 함수
def render_copyable_table(records, work_type, date_str, current_user, is_past_record=False):
    if not records:
        st.info("해당 날짜에 등록된 근무자가 없습니다.", icon=":material/info:")
        return
        
    font_family = "'맑은 고딕', 'Malgun Gothic', '돋움', Dotum, sans-serif"
    
    title_style = f"border: 1px solid #000000; font-family: {font_family}; font-size: 16px; font-weight: normal; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 10px;"
    red_alert_style = f"border: 1px solid #000000; font-family: {font_family}; font-size: 9pt; font-weight: bold; color: #FF0000; background-color: #ffffff; text-align: left; vertical-align: middle; padding: 6px; line-height: 1.4;"
    bold_style = f"border: 1px solid #000000; font-family: {font_family}; font-size: 11pt; font-weight: bold; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 6px;"
    normal_style = f"border: 1px solid #000000; font-family: {font_family}; font-size: 11pt; font-weight: normal; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 6px;"
    
    rows_html = ""
    for idx, (name, end_t, reason) in enumerate(records, start=1):
        time_str = f"17:30 ~ {end_t}" if work_type == "야간" else f"08:00 ~ {end_t}"
        
        actual_time_str = ""
        hr_str = ""
        
        if is_past_record:
            actual_time_str = time_str
            try:
                start_t = "17:30" if work_type == "야간" else "08:00"
                t1 = datetime.strptime(start_t, "%H:%M")
                t2 = datetime.strptime(end_t, "%H:%M")
                hr = (t2 - t1).total_seconds() / 3600.0
                if work_type == "휴일" and t2 > datetime.strptime("12:00", "%H:%M"):
                    hr -= 1.0
                hr_str = f"{hr:g}" 
            except ValueError:
                hr_str = ""
        
        rows_html += f"""
        <tr>
            <td style="{normal_style}">{idx}</td>
            <td colspan="2" style="{normal_style}">{name}</td>
            <td style="{normal_style}">{time_str}</td>
            <td style="{normal_style} text-align: left;">{reason}</td>
            <td style="{normal_style}">{actual_time_str}</td>
            <td style="{normal_style}">{hr_str}</td>
        </tr>
        """
    
    hiworks_url = "https://approval.office.hiworks.com/ohyoung.net/approval/document/write"
    
    html_string = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />
    <style>
        body {{ margin: 0; padding: 0; font-family: {font_family}; }}
        .btn-container {{ 
            display: flex; 
            gap: 10px; 
            margin-bottom: 10px; 
        }}
        .copy-btn, .link-btn {{
            flex: 1; 
            padding: 12px; 
            color: white; 
            border: none; 
            border-radius: 6px; 
            font-size: 15px; 
            cursor: pointer; 
            font-weight: bold;
            text-align: center;
            text-decoration: none;
            transition: background-color 0.3s; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            box-sizing: border-box;
        }}
        .copy-btn {{ background-color: #1b489d; }}
        .copy-btn:hover {{ background-color: #1b489d; }}
        
        .link-btn {{ background-color: #1b489d; }}
        .link-btn:hover {{ background-color: #16a34a; }}
    </style>
    </head>
    <body>
        <div class="btn-container">
            <button class="copy-btn" onclick="copyTable()">
                <span class="material-symbols-outlined" style="font-size: 18px;">content_copy</span>
                <span id="btn-text">표 복사하기</span>
            </button>
            <a href="{hiworks_url}" target="_blank" class="link-btn">
                <span class="material-symbols-outlined" style="font-size: 18px;">open_in_new</span>
                하이웍스 결재창 열기
            </a>
        </div>
        <div id="table-container">
            <table style="border-collapse: collapse; width: 100%;">
                <tbody>
                    <tr>
                        <td colspan="7" style="{title_style}">시간외근무</td>
                    </tr>
                    <tr>
                        <td colspan="2" rowspan="2" style="{bold_style}">소속부서</td>
                        <td rowspan="2" style="{normal_style}">T/S TEAM</td>
                        <td rowspan="2" style="{bold_style}">근무일</td>
                        <td rowspan="2" style="{normal_style}">{date_str}</td>
                        <td rowspan="2" style="{bold_style}">기안자</td>
                        <td rowspan="2" style="{normal_style}">{current_user}</td>
                    </tr>
                    <tr></tr>
                    <tr>
                        <td colspan="7" style="{red_alert_style}">
                            ※ 근무일: YYYY-MM-DD 형식 | HR: 숫자만 입력 (예: 2, 3.5) | 실근무시간: HH:MM~HH:MM 형식<br>
                            ※ 신청시간, 실근무시간, HR&nbsp;&nbsp;&nbsp;따옴표 " " 사용금지
                        </td>
                    </tr>
                    <tr>
                        <td style="{bold_style} width: 5%;">No.</td>
                        <td colspan="2" style="{bold_style} width: 15%;">성명</td>
                        <td style="{bold_style} width: 20%;">신청시간</td>
                        <td style="{bold_style} width: 30%;">근무사유</td>
                        <td style="{bold_style} width: 20%;">실근무시간</td>
                        <td style="{bold_style} width: 10%;">HR</td>
                    </tr>
                    {rows_html}
                </tbody>
            </table>
        </div>
        
        <script>
        function copyTable() {{
            var el = document.getElementById("table-container");
            var range = document.createRange();
            var sel = window.getSelection();
            sel.removeAllRanges();
            try {{
                range.selectNodeContents(el);
                sel.addRange(range);
            }} catch (e) {{
                range.selectNode(el);
                sel.addRange(range);
            }}
            document.execCommand("copy");
            sel.removeAllRanges();
            
            var btn = document.querySelector(".copy-btn");
            var btnText = document.getElementById("btn-text");
            var icon = btn.querySelector('.material-symbols-outlined');
            
            var originalText = btnText.innerText;
            
            icon.innerText = "check_circle";
            btnText.innerText = "복사 완료!";
            btn.style.backgroundColor = "#16a34a";
            
            setTimeout(function() {{
                icon.innerText = "content_copy";
                btnText.innerText = originalText;
                btn.style.backgroundColor = "#1b489d";
            }}, 2000);
        }}
        </script>
    </body>
    </html>
    """
    height = 300 + (len(records) * 35) 
    components.html(html_string, height=height, scrolling=True)


# --- 5. 세션 상태 관리 (로그인 처리) ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_user" not in st.session_state: st.session_state.current_user = None
if "login_selected_user" not in st.session_state: st.session_state.login_selected_user = ALL_USERS[0]

# 🔒 로그인 화면
if not st.session_state.logged_in:
    st.markdown("## :material/domain: T/S 근무 계획 관리 시스템")
    st.caption("Created by tskwon :material/science:")
    
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.write("")
        st.markdown("### :material/lock: 시스템 로그인")
        
        st.markdown("##### :material/person: 야근인원")
        with st.container():
            st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
            for user in members:
                btn_type = "primary" if user == st.session_state.login_selected_user else "secondary"
                if st.button(user, key=f"login_btn_{user}", use_container_width=True, type=btn_type):
                    st.session_state.login_selected_user = user
                    st.rerun()
                    
        st.write("")
        st.markdown("##### :material/shield_person: 관리자")
        with st.container():
            st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
            for user in admins:
                btn_type = "primary" if user == st.session_state.login_selected_user else "secondary"
                if st.button(user, key=f"login_btn_{user}", use_container_width=True, type=btn_type):
                    st.session_state.login_selected_user = user
                    st.rerun()
        
        st.write("")
        st.markdown(f"**현재 선택됨:** `{st.session_state.login_selected_user}`")
        
        with st.form("login_form", border=False):
            pin_input = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True, icon=":material/login:")
            
            if submitted:
                if USER_PINS.get(st.session_state.login_selected_user) == pin_input:
                    st.session_state.logged_in = True
                    st.session_state.current_user = st.session_state.login_selected_user
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.", icon=":material/error:")
    st.stop() 


# =====================================================================
# 로그인 성공 시 메인 화면
# =====================================================================

# ⭐️ 상단 헤더 및 로그아웃/비밀번호 변경 버튼 배치 (비율 조정)
top_col1, top_col2, top_col3 = st.columns([5.5, 1.5, 1.5])

with top_col1:
    st.markdown("## :material/domain: T/S 근무 계획 관리 시스템") 
    st.caption("Created by tskwon :material/science:")

with top_col2:
    # 팝오버를 사용해 로그아웃 버튼 옆에 깔끔하게 배치
    with st.popover("비밀번호 변경", icon=":material/key:", use_container_width=True):
        with st.form("change_pw_form", border=False):
            old_pw = st.text_input("현재 비밀번호", type="password", placeholder="기존 비밀번호")
            new_pw = st.text_input("새 비밀번호", type="password", placeholder="변경할 비밀번호")
            new_pw_confirm = st.text_input("새 비밀번호 확인", type="password", placeholder="한번 더 입력")
            
            submit_pw = st.form_submit_button("변경 적용", type="primary", use_container_width=True)
            
            if submit_pw:
                if old_pw != USER_PINS.get(st.session_state.current_user):
                    st.error("현재 비밀번호가 일치하지 않습니다.", icon=":material/error:")
                elif new_pw != new_pw_confirm:
                    st.error("새 비밀번호가 서로 일치하지 않습니다.", icon=":material/error:")
                elif len(new_pw) < 4:
                    st.error("보안을 위해 4자리 이상 입력해주세요.", icon=":material/warning:")
                elif old_pw == new_pw:
                    st.error("기존과 동일한 비밀번호입니다.", icon=":material/warning:")
                else:
                    row_index = -1
                    for i, row in enumerate(account_data):
                        if len(row) >= 1 and row[0] == st.session_state.current_user:
                            row_index = i + 1 
                            break
                    
                    if row_index != -1:
                        account_sheet.update_cell(row_index, 2, new_pw) 
                        st.success("변경 완료! 다시 로그인해주세요.", icon=":material/check_circle:")
                        time.sleep(1.5)
                        st.session_state.logged_in = False
                        st.session_state.current_user = None
                        st.rerun()
                    else:
                        st.error("계정 정보를 찾을 수 없습니다.", icon=":material/error:")

with top_col3:
    if st.button("로그아웃", use_container_width=True, icon=":material/logout:"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()
        
st.markdown("---") 


# --- 6. 고정 데이터 및 날짜 정의 ---
night_time_slots = ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]
holiday_time_slots = ["12:00", "17:00"] 

KST = timezone(timedelta(hours=9))
current_time = datetime.now(KST)
today_date = current_time.date()
today_str = today_date.strftime('%Y-%m-%d')

this_saturday_date = today_date + timedelta(days=(5 - today_date.weekday()))
this_saturday_str = this_saturday_date.strftime('%Y-%m-%d')


# --- 7. 기타 상태 관리 ---
if "night_end_time" not in st.session_state: st.session_state.night_end_time = night_time_slots[0]
if "night_reason" not in st.session_state: st.session_state.night_reason = ""

if "holiday_end_time" not in st.session_state or st.session_state.holiday_end_time not in holiday_time_slots: 
    st.session_state.holiday_end_time = holiday_time_slots[0]
if "holiday_reason" not in st.session_state: st.session_state.holiday_reason = ""


# --- 8. 화면 레이아웃 분할 ---
col1, col2 = st.columns([1, 1.5])

# 공통 뱃지(Badge) 색상 세팅
try:
    theme_primary = st.get_option("theme.primaryColor")
    if not theme_primary:
        theme_primary = "#ff4b4b" 
except:
    theme_primary = "#ff4b4b"
    
badge_style = f"background-color: {theme_primary}; color: white; border: 1px solid {theme_primary}; border-radius: 6px; padding: 3px 12px; font-size: 15px; font-weight: normal; margin-left: 8px;"


# ⭐️ 우측 화면(col2) 먼저 선언: 날짜 변수 확보
with col2:
    view_date = st.date_input("조회 및 상신 기준 날짜 선택", today_date)
    view_str = view_date.strftime('%Y-%m-%d')
    view_saturday_date = view_date + timedelta(days=(5 - view_date.weekday()))
    view_saturday_str = view_saturday_date.strftime('%Y-%m-%d')


# ⭐️ 좌측 화면(col1) 선언: 결재 상신 / 계획 등록
with col1:
    if st.session_state.current_user in admins:
        st.markdown(f"#### :material/inbox: 결재 상신 데이터 <span style='{badge_style}'>{st.session_state.current_user}</span>", unsafe_allow_html=True)
        
        daily_pw = get_daily_password(today_str)
        st.info(f"오늘({today_str})의 지각자 예외 암호: **{daily_pw}** (직원 문의 시 안내)", icon=":material/key:")
        
        # --- 야간 결재 상신 표 ---
        st.markdown("<hr style='margin: 15px 0px 10px 0px; border: none; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)
        st.markdown(f"##### :material/dark_mode: 야간 상신 ({view_str})")
        
        records_night = []
        for row in all_data[1:]:
            if len(row) >= 4 and row[2] == view_str:
                row_wt = get_work_type(row) 
                if row_wt == "야간":
                    row_name = row[1]
                    row_end_time = row[3]
                    reason = row[4] if len(row) >= 5 and row[4].strip() != "" else "업무 연장"
                    records_night.append((row_name, row_end_time, reason))
        
        records_night.sort(key=lambda x: members.index(x[0]) if x[0] in members else 999)
        
        is_viewing_today = (view_date == today_date)
        download_avail_time = current_time.replace(hour=12, minute=10, second=0, microsecond=0)
        
        if is_viewing_today and current_time < download_avail_time:
            st.warning("금일 야간 전자결재 상신(복사)은 **12:10분 이후**부터 활성화됩니다.", icon=":material/warning:")
        else:
            is_past = (view_date < today_date)
            render_copyable_table(records_night, "야간", view_str, st.session_state.current_user, is_past)
            
    else:
        st.markdown(f"#### :material/edit_document: 계획 등록 <span style='{badge_style}'>{st.session_state.current_user}</span>", unsafe_allow_html=True)
        
        tabs = st.tabs([":material/dark_mode: 야간근무", ":material/light_mode: 휴일근무"])
        tab_night, tab_holiday = tabs[0], tabs[1]
        
        with tab_night:
            deadline_time = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
            is_past_deadline = current_time >= deadline_time
            form_disabled = False
            
            if is_past_deadline:
                daily_pw = get_daily_password(today_str)
                st.error("금일 야간근무 등록 및 수정이 마감되었습니다. (12:00 마감)", icon=":material/error:")
                
                override_input = st.text_input("지각자 예외 등록 암호 (관리자에게 문의)", type="password", key="override_pw")
                
                if override_input == daily_pw:
                    st.success("예외 암호 확인! 등록 및 수정이 가능합니다.", icon=":material/check_circle:")
                    form_disabled = False 
                else:
                    if override_input:
                        st.error("암호가 일치하지 않습니다.", icon=":material/error:")
                    form_disabled = True 
            else:
                time_diff = deadline_time - current_time
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                st.info(f"등록 마감까지 **{hours}시간 {minutes}분** 남았습니다. (12:00 마감)", icon=":material/hourglass_empty:")
            
            st.caption(f"오늘(**{today_str}**) 기준으로 야근이 등록됩니다.")
            st.markdown("**1. 종료 시간을 선택하세요**")
            with st.container():
                st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
                for t_slot in night_time_slots:
                    btn_type = "primary" if t_slot == st.session_state.night_end_time else "secondary"
                    if st.button(t_slot, key=f"n_{t_slot}", use_container_width=True, type=btn_type, disabled=form_disabled):
                        st.session_state.night_end_time = t_slot
                        st.rerun()
                        
            st.markdown("**2. 근무 사유를 입력하세요**")
            st.text_input("사유 입력", key="night_reason", label_visibility="collapsed", placeholder="예: B/T 3건 및 견뢰도 Test", disabled=form_disabled)

            with st.container():
                st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
                if st.button(f"야간 등록/수정", key="n_reg", type="primary", use_container_width=True, disabled=form_disabled, icon=":material/save:"):
                    if not st.session_state.night_reason.strip():
                        st.error("근무 사유를 반드시 적어주세요!", icon=":material/warning:")
                    else:
                        row_to_update = -1
                        for i, row in enumerate(all_data):
                            row_wt = get_work_type(row)
                            if i > 0 and len(row) >= 4 and row[1] == st.session_state.current_user and row[2] == today_str and row_wt == "야간":
                                row_to_update = i + 1 
                                break
                        if row_to_update != -1:
                            sheet.update_cell(row_to_update, 4, st.session_state.night_end_time) 
                            sheet.update_cell(row_to_update, 5, st.session_state.night_reason)
                            sheet.update_cell(row_to_update, 6, "야간") 
                            st.success(f"야간근무 변경 완료!", icon=":material/sync:")
                        else:
                            new_id = len(all_data)
                            sheet.append_row([new_id, st.session_state.current_user, today_str, st.session_state.night_end_time, st.session_state.night_reason, "야간"])
                            st.success(f"야간근무 등록 완료!", icon=":material/celebration:")
                        st.rerun()
                    
                if st.button(f"야간 취소", key="n_del", type="secondary", use_container_width=True, disabled=form_disabled, icon=":material/delete:"):
                    row_to_delete = -1
                    for i, row in enumerate(all_data):
                        row_wt = get_work_type(row)
                        if i > 0 and len(row) >= 4 and row[1] == st.session_state.current_user and row[2] == today_str and row_wt == "야간":
                            row_to_delete = i + 1
                            break
                    if row_to_delete != -1:
                        sheet.delete_rows(row_to_delete)
                        st.warning(f"야간근무 취소 완료!", icon=":material/delete:")
                    else:
                        st.info(f"기록 없음", icon=":material/info:")
                    st.rerun()

        with tab_holiday:
            st.caption(f"이번 주 토요일(**{this_saturday_str}**) 기준으로 휴일근무가 등록됩니다.")
            st.markdown("**1. 종료 시간을 선택하세요**")
            with st.container():
                st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
                for t_slot in holiday_time_slots:
                    btn_type = "primary" if t_slot == st.session_state.holiday_end_time else "secondary"
                    if st.button(t_slot, key=f"h_{t_slot}", use_container_width=True, type=btn_type):
                        st.session_state.holiday_end_time = t_slot
                        st.rerun()
                        
            st.markdown("**2. 근무 사유를 입력하세요**")
            st.text_input("사유 입력", key="holiday_reason", label_visibility="collapsed", placeholder="예: 공장 라인 점검")

            with st.container():
                st.markdown('<style data-target="btn-grid"></style>', unsafe_allow_html=True)
                if st.button(f"휴일 등록/수정", key="h_reg", type="primary", use_container_width=True, icon=":material/save:"):
                    if not st.session_state.holiday_reason.strip():
                        st.error("근무 사유를 반드시 적어주세요!", icon=":material/warning:")
                    else:
                        row_to_update = -1
                        for i, row in enumerate(all_data):
                            row_wt = get_work_type(row)
                            if i > 0 and len(row) >= 4 and row[1] == st.session_state.current_user and row[2] == this_saturday_str and row_wt == "휴일":
                                row_to_update = i + 1 
                                break
                        if row_to_update != -1:
                            sheet.update_cell(row_to_update, 4, st.session_state.holiday_end_time) 
                            sheet.update_cell(row_to_update, 5, st.session_state.holiday_reason)
                            sheet.update_cell(row_to_update, 6, "휴일") 
                            st.success(f"휴일근무 변경 완료!", icon=":material/sync:")
                        else:
                            new_id = len(all_data)
                            sheet.append_row([new_id, st.session_state.current_user, this_saturday_str, st.session_state.holiday_end_time, st.session_state.holiday_reason, "휴일"])
                            st.success(f"휴일근무 등록 완료!", icon=":material/celebration:")
                        st.rerun()
                    
                if st.button(f"휴일 취소", key="h_del", type="secondary", use_container_width=True, icon=":material/delete:"):
                    row_to_delete = -1
                    for i, row in enumerate(all_data):
                        row_wt = get_work_type(row)
                        if i > 0 and len(row) >= 4 and row[1] == st.session_state.current_user and row[2] == this_saturday_str and row_wt == "휴일":
                            row_to_delete = i + 1
                            break
                    if row_to_delete != -1:
                        sheet.delete_rows(row_to_delete)
                        st.warning(f"휴일근무 취소 완료!", icon=":material/delete:")
                    else:
                        st.info(f"기록 없음", icon=":material/info:")
                    st.rerun()

# ⭐️ 다시 우측 화면(col2) 선언: 하단 현황판 및 달력 렌더링
with col2:
    if st.session_state.current_user in admins:
        tab1, tab2 = st.tabs([":material/dark_mode: 야간 현황", ":material/calendar_month: 8주 달력 조회"])
    else:
        tab1, tab2 = st.tabs([":material/dark_mode: 야간 현황", ":material/calendar_month: 나의 8주 달력"])
    
    # === 탭 1: 야간근무 현황 ===
    with tab1:
        grid_df = pd.DataFrame(index=night_time_slots, columns=members).fillna("")
        records_night_view = []
        
        for row in all_data[1:]:
            if len(row) >= 4 and row[2] == view_str:
                row_wt = get_work_type(row) 
                if row_wt == "야간":
                    row_name = row[1]
                    row_end_time = row[3]
                    reason = row[4] if len(row) >= 5 and row[4].strip() != "" else "업무 연장"
                    records_night_view.append((row_name, row_end_time, reason))
        
        records_night_view.sort(key=lambda x: members.index(x[0]) if x[0] in members else 999)
        
        for name, end_t, reason in records_night_view:
            if end_t in grid_df.index and name in grid_df.columns:
                grid_df.loc[end_t, name] = "야근"
                    
        html_code = f'<table class="custom-overtime-table"><thead><tr><th>시간</th>'
        for col in grid_df.columns: html_code += f'<th>{col}</th>'
        html_code += '</tr></thead><tbody>'
        for index, row in grid_df.iterrows():
            html_code += f'<tr><th>{index}</th>'
            for val in row:
                html_code += f'<td class="overtime-checked">{val}</td>' if val == "야근" else f'<td>{val}</td>'
            html_code += '</tr>'
        html_code += '</tbody></table>'
        st.markdown(html_code, unsafe_allow_html=True)

    # === 탭 2: 요일별 8주 달력 ===
    with tab2:
        current_week_start = view_date - timedelta(days=view_date.weekday())
        weeks_info = []
        for i in range(7, -1, -1):
            w_start = current_week_start - timedelta(weeks=i)
            w_end = w_start + timedelta(days=6)
            label = f"{w_start.strftime('%m/%d')} ~ {w_end.strftime('%m/%d')}"
            weeks_info.append({"start": w_start, "end": w_end, "label": label})
            
        def calculate_work_hours(end_time_str, work_type):
            try:
                end = datetime.strptime(end_time_str, "%H:%M")
                if work_type == "야간":
                    start = datetime.strptime("17:30", "%H:%M")
                    hours = (end - start).total_seconds() / 3600.0
                else:
                    start = datetime.strptime("08:00", "%H:%M")
                    hours = (end - start).total_seconds() / 3600.0
                    if end > datetime.strptime("12:00", "%H:%M"):
                        hours -= 1.0
                        
                return max(hours, 0.0) 
            except ValueError:
                return 0.0

        if st.session_state.current_user in admins:
            default_index = HOLIDAY_USERS.index(st.session_state.current_user)
            target_user = st.selectbox("조회할 인원을 선택하세요", HOLIDAY_USERS, index=default_index)
        else:
            st.caption(f"이 데이터는 오직 **{st.session_state.current_user}** 님에게만 표시됩니다.")
            target_user = st.session_state.current_user

        calendar_data = { w["label"]: [0.0] * 7 for w in weeks_info }

        for row in all_data[1:]: 
            if len(row) >= 4:
                try:
                    row_name = row[1]
                    if row_name == target_user:
                        row_date = datetime.strptime(row[2], "%Y-%m-%d").date()
                        row_end_time = row[3]
                        row_wt = get_work_type(row) 
                        
                        if weeks_info[0]["start"] <= row_date <= weeks_info[-1]["end"]:
                            for w in weeks_info:
                                if w["start"] <= row_date <= w["end"]:
                                    if row_wt == "휴일":
                                        day_idx = 5
                                    else:
                                        day_idx = row_date.weekday()
                                        
                                    calendar_data[w["label"]][day_idx] += calculate_work_hours(row_end_time, row_wt)
                                    break
                except ValueError:
                    continue
        
        weekly_html = '''
        <table class="weekly-summary-table">
            <colgroup>
                <col style="width: 26%;">
                <col style="width: 10%;">
                <col style="width: 10%;">
                <col style="width: 10%;">
                <col style="width: 10%;">
                <col style="width: 10%;">
                <col style="width: 10%;">
                <col style="width: 14%;">
            </colgroup>
            <thead>
                <tr>
                    <th>주차 (기간)</th>
                    <th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th>토</th>
                    <th>합계</th>
                </tr>
            </thead>
            <tbody>
        '''
        
        for w in weeks_info:
            label = w["label"]
            days = calendar_data[label][:6] 
            week_total = sum(days)
            
            weekly_html += f'<tr><td class="weekly-label">{label}</td>'
            
            for d in days:
                display_d = f"{d:.1f}h" if d > 0 else "-"
                weekly_html += f'<td>{display_d}</td>'
                
            display_total = f"{week_total:.1f}h" if week_total > 0 else "-"
            weekly_html += f'<td class="weekly-hours">{display_total}</td></tr>'
            
        weekly_html += '</tbody></table>'
        st.markdown(weekly_html, unsafe_allow_html=True)
