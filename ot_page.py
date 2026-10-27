"""야근계획 (T/S 근무 관리) — 로그인 이후 화면

★ 이 파일은 '야근계획_Firebase' 폴더(폰용 Streamlit Cloud 앱)와 '통합프로그램/views' 폴더에
   똑같은 내용으로 들어 있습니다. 고칠 때는 두 곳 모두 같은 파일로 바꿔 주세요.
   데이터 읽기/쓰기는 ot_store.py (Firebase 원본 + 구글 시트 사본)
"""
from datetime import datetime, timedelta, timezone
import random
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:  # 통합 프로그램(views 폴더) / 야근계획 단독 앱 모두에서 불러올 수 있게
    from . import ot_store
except ImportError:
    import ot_store

# ⭐️ 사용자 및 관리자 정의 (명단은 여기 한 곳에서만 관리)
members = ["권회준", "김민호", "오진영", "강한수", "최지훈", "박현수", "테이", "라나", "이르판"]
admins = ["장현준", "김동기", "최상철", "강택규", "김현준"]
ALL_USERS = members + admins
HOLIDAY_USERS = admins + members
KST = timezone(timedelta(hours=9))
NIGHT_START, HOLIDAY_START = "17:30", "08:00"
get_work_type = ot_store.get_work_type
OY_FONT_FACES = ""  # 표 복사 버튼 글꼴 (main()에서 넘겨받음)


def _inject_css(css):
    css = "\n".join(l for l in re.sub(r"/\*.*?\*/", "", css, flags=re.S).splitlines() if l.strip())
    st.markdown(css, unsafe_allow_html=True)


def data_range(view_date, today_date):
    """현황표 · 8주 달력에 필요한 기간만 읽기 (조회 날짜 기준 9주 전 ~ 2주 뒤)"""
    s = min(view_date, today_date) - timedelta(weeks=9)
    e = max(view_date, today_date) + timedelta(days=13)
    return s.isoformat(), e.isoformat()


def get_daily_password(date_str):
    random.seed(date_str + "_TS_TEAM_SECRET")
    pw = str(random.randint(1000, 9999))
    random.seed() 
    return pw


# ⭐️ 근무 시간 계산 (메인 화면 요약에서도 사용)
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


# ⭐️ 야근계획 화면 전용 스타일 (글꼴·상단바는 공통)
PAGE_CSS = """
<style>
    .stTabs [data-baseweb="tab-panel"] { padding-top: 0.5rem !important; }
    
    .custom-overtime-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 14.5px; table-layout: fixed; }
    .custom-overtime-table th, .custom-overtime-table td { border: 1px solid #dcdde1; padding: 6px 2px; text-align: center !important; vertical-align: middle !important; }
    .custom-overtime-table th { background-color: #f0f2f6; color: #31333F; font-weight: bold; }
    .overtime-checked { background-color: #fff5f5; color: #ff4b4b; font-weight: bold; }
    
    @media (max-width: 768px) {
        .custom-overtime-table { font-size: 2.8vw !important; }
        .custom-overtime-table th, .custom-overtime-table td { padding: 4px 0px !important; height: 30px; white-space: nowrap !important; letter-spacing: -0.5px !important; }
        .overtime-checked { font-size: 2.6vw !important; letter-spacing: -1px !important; }
    }
    
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) {
        display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 6px !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:not(:has(style)) {
        width: calc(50% - 3px) !important; flex: 0 0 calc(50% - 3px) !important; min-width: 0 !important; 
    }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:has(style) { display: none !important; }
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) button {
        white-space: nowrap !important; height: auto !important; min-height: 38px !important; padding: 0 !important;
    }
    
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


# ⭐️ 표 렌더링 함수
def render_copyable_table(records, work_type, date_str, current_user, is_past_record=False):
    if not records:
        st.info("해당 날짜에 등록된 근무자가 없습니다.", icon=":material/info:")
        return
        
    font_family = "'Apple SD Gothic Neo', '맑은 고딕', 'Malgun Gothic', '돋움', Dotum, sans-serif"
    
    title_style = f"border: 1px solid #000000; font-family: {font_family}; font-size: 16px; font-weight: normal; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 10px;"
    red_alert_style = f"border: 1px solid #000000; font-family: {font_family}; font-size: 9pt; font-weight: bold; color: #FF0000; background-color: #ffffff; text-align: left; vertical-align: middle; padding: 6px; line-height: 1.4;"
    bold_style = f"border: 1px solid #000000; font-family: {font_family}; font-size: 11pt; font-weight: bold; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 6px;"
    normal_style = f"border: 1px solid #000000; font-family: {font_family}; font-size: 11pt; font-weight: normal; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 6px;"

    bold_style_13px = f"border: 1px solid #000000; font-family: {font_family}; font-size: 13px; font-weight: bold; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 6px;"
    normal_style_13px = f"border: 1px solid #000000; font-family: {font_family}; font-size: 13px; font-weight: normal; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 6px;"
    data_style_13px = f"border: 1px solid #000000; font-family: {font_family}; font-size: 13px; font-weight: normal; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 6px;"
    
    # ✅ 1. 기입되는 내용을 위한 13px 크기의 새로운 스타일 추가
    data_style_13px = f"border: 1px solid #000000; font-family: {font_family}; font-size: 13px; font-weight: normal; color: #000000; background-color: #ffffff; text-align: center; vertical-align: middle; padding: 6px;"
    
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
        
        # ✅ 2. HTML 행(row) 생성 부분 수정
        # 첫 번째 열({idx})은 기존 normal_style(11pt)을 유지하고, 나머지는 data_style_13px 적용
        rows_html += f'<tr>'
        rows_html += f'<td style="{normal_style}">{idx}</td>'
        rows_html += f'<td colspan="2" style="{data_style_13px}">{name}</td>'
        rows_html += f'<td style="{data_style_13px}">{time_str}</td>'
        rows_html += f'<td style="{data_style_13px} text-align: left;">{reason}</td>'
        rows_html += f'<td style="{data_style_13px}">{actual_time_str}</td>'
        rows_html += f'<td style="{data_style_13px}">{hr_str}</td>'
        rows_html += f'</tr>'
        
        
    
    hiworks_url = "https://approval.office.hiworks.com/ohyoung.net/approval/document/write"
    
    html_string = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />
    <style>
        {OY_FONT_FACES}
        body {{ margin: 0; padding: 0; font-family: {font_family}; }}
        .btn-container {{ display: flex; gap: 10px; margin-bottom: 10px; }}
        .copy-btn, .link-btn {{
            flex: 1; padding: 12px; color: white; border: none; border-radius: 6px; 
            font-size: 15px; cursor: pointer; font-weight: bold; text-align: center;
            text-decoration: none; transition: background-color 0.3s; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; align-items: center;
            justify-content: center; gap: 6px; box-sizing: border-box; font-family: 'OY Outfit', 'OY NanumSquare Neo', {font_family};
        }}
        .copy-btn {{ background-color: #1b489d; }}
        .copy-btn:hover {{ background-color: #153b82; }}
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
        
        <table id="table-display" style="border-collapse: collapse; width: 100%; table-layout: fixed;">
            <colgroup>
                <col style="width: 5%;">
                <col style="width: 7.5%;">
                <col style="width: 7.5%;">
                <col style="width: 20%;">
                <col style="width: 30%;">
                <col style="width: 20%;">
                <col style="width: 10%;">
            </colgroup>
            <tbody>
                <tr>
                    <td colspan="7" style="{title_style}">시간외근무</td>
                </tr>
                <!-- ✅ 수정한 부분: bold_style -> bold_style_13px / normal_style -> normal_style_13px 로 변경 -->
                <tr>
                    <td colspan="2" rowspan="2" style="{bold_style_13px}">소속부서</td>
                    <td rowspan="2" style="{normal_style_13px}">T/S TEAM</td>
                    <td rowspan="2" style="{bold_style_13px}">근무일</td>
                    <td rowspan="2" style="{normal_style_13px}">{date_str}</td>
                    <td rowspan="2" style="{bold_style_13px}">기안자</td>
                    <td rowspan="2" style="{normal_style_13px}">{current_user}</td>
                </tr>
                <tr></tr>
                <tr>
                    <td colspan="7" style="{red_alert_style}">※ 근무일: YYYY-MM-DD 형식 | HR: 숫자만 입력 (예: 2, 3.5) | 실근무시간: HH:MM~HH:MM 형식<br>※ 신청시간, 실근무시간, HR&nbsp;&nbsp;&nbsp;따옴표 " " 사용금지</td>
                </tr>
                <tr>
                    <td style="{bold_style}">No.</td>
                    <td colspan="2" style="{bold_style}">성명</td>
                    <td style="{bold_style}">신청시간</td>
                    <td style="{bold_style}">근무사유</td>
                    <td style="{bold_style}">실근무시간</td>
                    <td style="{bold_style}">HR</td>
                </tr>
                {rows_html}
            </tbody>
        </table>

        <script>
        function copyTable() {{
            var el = document.getElementById("table-display");
            
            var handleCopy = function(e) {{
                var htmlData = "<html><head><meta charset='utf-8'></head><body>" + el.outerHTML + "</body></html>";
                e.clipboardData.setData("text/html", htmlData);
                e.preventDefault(); 
            }};
            
            document.addEventListener("copy", handleCopy);
            
            var range = document.createRange();
            var sel = window.getSelection();
            sel.removeAllRanges();
            try {{ range.selectNodeContents(el); sel.addRange(range); }} 
            catch (e) {{ range.selectNode(el); sel.addRange(range); }}
            
            document.execCommand("copy"); 
            
            document.removeEventListener("copy", handleCopy);
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


def main(font_faces=""):
    global OY_FONT_FACES
    OY_FONT_FACES = font_faces
    _inject_css(PAGE_CSS)

    # --- 6. 고정 데이터 및 날짜 정의 ---
    night_time_slots = ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]
    holiday_time_slots = ["12:00", "17:00"] 

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

    try:
        with st.spinner("데이터를 불러오는 중입니다..."):
            all_data = ot_store.load_data(*data_range(view_date, today_date))
    except Exception as e:
        st.error("데이터 저장소(Firebase / 구글 시트)에 연결하지 못했습니다. 키 설정을 확인해 주세요.", icon=":material/cloud_off:")
        with st.expander("오류 내용"):
            st.code(str(e))
        return


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
            download_avail_time = current_time.replace(hour=12, minute=55, second=0, microsecond=0)

            if view_date > today_date:
                st.warning(f"미래 날짜({view_str})의 결재 상신은 아직 불가능합니다. (해당일 12:55 이후 가능)", icon=":material/warning:")
            elif is_viewing_today and current_time < download_avail_time:
                st.warning("금일 야간 전자결재 상신(복사)은 **12:55분 이후**부터 활성화됩니다.", icon=":material/warning:")
            else:
                is_past = (view_date < today_date)
                render_copyable_table(records_night, "야간", view_str, st.session_state.current_user, is_past)

        else:
            st.markdown(f"#### :material/edit_document: 계획 등록 <span style='{badge_style}'>{st.session_state.current_user}</span>", unsafe_allow_html=True)

            tabs = st.tabs([":material/dark_mode: 야간근무", ":material/light_mode: 휴일근무"])
            tab_night, tab_holiday = tabs[0], tabs[1]

            with tab_night:
                deadline_time = current_time.replace(hour=12, minute=50, second=0, microsecond=0)
                is_past_deadline = current_time >= deadline_time
                form_disabled = False

                if is_past_deadline:
                    daily_pw = get_daily_password(today_str)
                    st.error("금일 야간근무 등록 및 수정이 마감되었습니다. (12:50 마감)", icon=":material/error:")

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
                    st.info(f"등록 마감까지 **{hours}시간 {minutes}분** 남았습니다. (12:50 마감)", icon=":material/hourglass_empty:")

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
                            res = ot_store.save(st.session_state.current_user, today_str, "야간",
                                                st.session_state.night_end_time, st.session_state.night_reason)
                            st.toast(f"야간근무 {res} 완료!", icon=":material/check_circle:")
                            st.rerun()

                    if st.button(f"야간 취소", key="n_del", type="secondary", use_container_width=True, disabled=form_disabled, icon=":material/delete:"):
                        if ot_store.delete(st.session_state.current_user, today_str, "야간"):
                            st.toast("야간근무 취소 완료!", icon=":material/delete:")
                        else:
                            st.toast("취소할 기록이 없습니다.", icon=":material/info:")
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
                            res = ot_store.save(st.session_state.current_user, this_saturday_str, "휴일",
                                                st.session_state.holiday_end_time, st.session_state.holiday_reason)
                            st.toast(f"휴일근무 {res} 완료!", icon=":material/check_circle:")
                            st.rerun()

                    if st.button(f"휴일 취소", key="h_del", type="secondary", use_container_width=True, icon=":material/delete:"):
                        if ot_store.delete(st.session_state.current_user, this_saturday_str, "휴일"):
                            st.toast("휴일근무 취소 완료!", icon=":material/delete:")
                        else:
                            st.toast("취소할 기록이 없습니다.", icon=":material/info:")
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
        st.caption(ot_store.status_text())
