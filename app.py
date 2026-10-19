import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta, timezone
import json
import gspread
from google.oauth2.service_account import Credentials
import random
import time

# ⭐️ 1. 모바일/PC 넓게 쓰기 설정
st.set_page_config(
    page_title="T/S 근무 관리",       
    page_icon="🗓️", 
    layout="wide", 
    initial_sidebar_state="collapsed" 
)

# ⭐️ 글꼴: 영어·숫자 = Outfit, 한글 = 나눔스퀘어 네오 (저장소 static/fonts 폴더의 글꼴 파일)
#    Streamlit Cloud: .streamlit/config.toml 의 enableStaticServing 으로 static 폴더를 내보냄
#    (config 없이 내 PC에서 실행하면 PC 안에서만 쓰는 통로로 내보냄 · 글꼴 파일이 없으면 기존 글꼴)
import os, re as _re, base64 as _b64
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR = os.path.join(_APP_DIR, "static", "fonts")
_OY_NEO = [("aLt", "100 349"), ("bRg", "350 549"), ("cBd", "550 749"), ("dEb", "750 849"), ("eHv", "850 900")]
_OY_OUTFIT = "outfit-latin-wght-normal.woff2"
_OY_UR = ("U+0000-001F,U+0021-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,"
          "U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD")

@st.cache_resource
def _oy_font_server():
    import threading, functools
    from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
    class _H(SimpleHTTPRequestHandler):
        def do_GET(self):
            _name = self.path.split("?")[0].lstrip("/")
            if "/" in _name or "\\" in _name or not _name.lower().endswith(".woff2"):
                self.send_error(404); return
            return super().do_GET()
        def end_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "max-age=31536000")
            super().end_headers()
        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_H, directory=_FONT_DIR))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"

def _oy_font_base():
    if not os.path.exists(os.path.join(_FONT_DIR, "NanumSquareNeoTTF-bRg.woff2")):
        return ""
    try:
        if st.get_option("server.enableStaticServing"):
            return "app/static/fonts"
    except Exception:
        pass
    try:
        return _oy_font_server()
    except Exception:
        return ""

_FONT_BASE = _oy_font_base()
OY_FONT_FACES = ""
if _FONT_BASE:
    OY_FONT_FACES = (f"@font-face {{ font-family: 'OY Outfit'; font-style: normal; font-weight: 100 900; font-display: swap; "
                     f"src: url('{_FONT_BASE}/{_OY_OUTFIT}') format('woff2-variations'), url('{_FONT_BASE}/{_OY_OUTFIT}') format('woff2'); unicode-range: {_OY_UR}; }}\n"
                     + "\n".join(f"@font-face {{ font-family: 'OY NanumSquare Neo'; font-style: normal; font-weight: {_w}; font-display: swap; "
                                 f"src: url('{_FONT_BASE}/NanumSquareNeoTTF-{_c}.woff2') format('woff2'); }}" for _c, _w in _OY_NEO))
    # 입력칸 · 버튼 · 탭 등 Streamlit 기본 글자도 같은 글꼴로 (config.toml에 이미 있으면 그대로)
    try:
        from streamlit import config as _st_config
        _THEME_FONT = "OY Outfit, OY NanumSquare Neo, sans-serif"
        if _st_config.get_option("theme.font") != _THEME_FONT or _FONT_BASE not in str(_st_config.get_option("theme.fontFaces") or ""):
            _st_config.set_option("theme.fontFaces",
                [{"family": "OY Outfit", "url": f"{_FONT_BASE}/{_OY_OUTFIT}", "weight": "100 900", "unicodeRange": _OY_UR}]
                + [{"family": "OY NanumSquare Neo", "url": f"{_FONT_BASE}/NanumSquareNeoTTF-{_c}.woff2", "weight": _w} for _c, _w in _OY_NEO])
            _st_config.set_option("theme.font", _THEME_FONT)
            st.rerun()
    except Exception:
        pass

def _logo_b64():
    for _p in ("logo1.png", "logo.png"):
        try:
            with open(os.path.join(_APP_DIR, _p), "rb") as _f:
                return _b64.b64encode(_f.read()).decode()
        except Exception:
            pass
    return ""

# ⭐️ 2. 사용자 및 관리자 정의
members = ["권회준", "김민호", "오진영", "강한수", "최지훈", "박현수", "테이", "라나", "이르판"]
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

doc = init_connection()
sheet = doc.sheet1                       

def get_work_type(row):
    if len(row) >= 6 and row[5].strip() != "":
        return row[5].strip()
    if len(row) >= 4 and row[3] in ["12:00", "17:00"]:
        return "휴일"
    return "야간"

# ⭐️ 4. CSS 스타일 전역 주입
font_family = "'OY Outfit', 'OY NanumSquare Neo', 'Apple SD Gothic Neo', '맑은 고딕', 'Malgun Gothic', '돋움', Dotum, sans-serif"

custom_css = f"""
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />
<style>
    __OY_FONT_FACES__
    .stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
    .stApp [data-testid="stMarkdownContainer"], .stApp table {{ font-family: {font_family}; }}

    /* ---------- 상단 바 (Spectra50 · SpectraMatch · UV-Vis · Dye Finder와 같은 네이비 고정 바) ---------- */
    .stApp .block-container {{ padding-top: 76px !important; }}
    .block-container [data-testid="stLayoutWrapper"]:has(> .st-key-topbar),
    .block-container > div > [data-testid="stVerticalBlock"] > div:has(> .st-key-topbar),
    .block-container [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style):not(:has(p, img, span, table)) {{ margin-bottom: -1rem !important; }}
    .st-key-topbar {{
        position: fixed !important; top: 0; left: 0; right: 0; height: 60px; z-index: 999990;
        background: linear-gradient(100deg, #1b489d 0%, #2557b8 100%);
        margin: 0 !important; padding: 0 20px !important; box-shadow: 0 4px 18px rgba(19,55,119,.28);
        display: flex; flex-direction: column; justify-content: center;
    }}
    .st-key-topbar [data-testid="stHorizontalBlock"] {{ align-items: center; flex-wrap: nowrap !important; gap: 8px !important; }}
    .st-key-topbar [data-testid="stHorizontalBlock"] > div:nth-child(1) {{ flex: 1 1 auto !important; width: auto !important; min-width: 0 !important; }}
    .st-key-topbar [data-testid="stHorizontalBlock"] > div:nth-child(2) {{ flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }}
    .oy-brand {{ display: flex; align-items: center; gap: 12px; color: #fff; white-space: nowrap; transform: translateY(-8px); min-width: 0; }}
    .oy-brand img {{ height: 38px; width: auto; max-width: 160px; object-fit: contain; }}
    .oy-brand .mark {{ width: 34px; height: 34px; border-radius: 9px; background: rgba(255,255,255,.15); color: #fff; display: flex; align-items: center; justify-content: center; }}
    .oy-brand .t1 {{ font-size: 21px; font-weight: 800; letter-spacing: -.3px; line-height: 1; color: #fff; }}
    .oy-brand .sub {{ font-size: 12px; font-weight: 600; color: #fff; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.22); padding: 3px 10px; border-radius: 999px; }}
    .oy-brand .material-symbols-outlined {{ font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important; font-feature-settings: 'liga'; line-height: 1; }}
    .stApp .st-key-topbar .stButton > button {{
        background: transparent !important; color: #fff !important; border: 1px solid rgba(255,255,255,.35) !important;
        border-radius: 9px !important; height: 36px !important; min-height: 36px !important; padding: 0 14px !important; box-shadow: none !important; white-space: nowrap;
    }}
    .stApp .st-key-topbar .stButton > button:hover {{ background: rgba(255,255,255,.14) !important; border-color: rgba(255,255,255,.6) !important; }}
    .stApp .st-key-topbar .stButton > button * {{ color: #fff !important; }}
    .st-key-oy_hidebadge {{ position: absolute !important; width: 0 !important; height: 0 !important; overflow: hidden !important; margin: 0 !important; }}
    @media (max-width: 768px) {{
        .st-key-topbar {{ padding: 0 12px !important; }}
        .oy-brand img {{ height: 30px; }}
        .oy-brand .t1 {{ font-size: 17px; }}
        .oy-brand .sub {{ display: none; }}
    }}
    [data-testid="stToolbar"], [data-testid="stAppDeployButton"], 
    [data-testid="stStatusWidget"], [data-testid="stDecoration"], 
    [data-testid="collapsedControl"], header[data-testid="stHeader"] {{ 
        display: none !important; 
    }}
    ::-webkit-scrollbar {{ width: 0px; height: 0px; background: transparent; }}
    html, body {{ -ms-overflow-style: none; scrollbar-width: none; overflow-x: hidden; font-family: {font_family}; }}
    
    .stApp, .block-container {{ padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 100vw !important; }}
    
    @media (max-width: 768px) {{
        .block-container {{ padding-left: 0.8rem !important; padding-right: 0.8rem !important; }}
        h1, h2, h3 {{ white-space: normal !important; word-break: keep-all !important; font-size: 6vw !important; letter-spacing: -0.5px !important; }}
    }}
    
    .stTabs [data-baseweb="tab-panel"] {{ padding-top: 0.5rem !important; }}
    
    .custom-overtime-table {{ width: 100%; border-collapse: collapse; text-align: center; font-size: 14.5px; table-layout: fixed; }}
    .custom-overtime-table th, .custom-overtime-table td {{ border: 1px solid #dcdde1; padding: 6px 2px; text-align: center !important; vertical-align: middle !important; }}
    .custom-overtime-table th {{ background-color: #f0f2f6; color: #31333F; font-weight: bold; }}
    .overtime-checked {{ background-color: #fff5f5; color: #ff4b4b; font-weight: bold; }}
    
    @media (max-width: 768px) {{
        .custom-overtime-table {{ font-size: 2.8vw !important; }}
        .custom-overtime-table th, .custom-overtime-table td {{ padding: 4px 0px !important; height: 30px; white-space: nowrap !important; letter-spacing: -0.5px !important; }}
        .overtime-checked {{ font-size: 2.6vw !important; letter-spacing: -1px !important; }}
    }}
    
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) {{
        display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 6px !important;
    }}
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:not(:has(style)) {{
        width: calc(50% - 3px) !important; flex: 0 0 calc(50% - 3px) !important; min-width: 0 !important; 
    }}
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) > div[data-testid="stElementContainer"]:has(style) {{ display: none !important; }}
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] style[data-target="btn-grid"]) button {{
        white-space: nowrap !important; height: auto !important; min-height: 38px !important; padding: 0 !important;
    }}
    
    .weekly-summary-table {{ width: 100%; text-align: center; font-size: 13.5px; margin-top: 5px; border-collapse: collapse; table-layout: fixed; }}
    .weekly-summary-table th, .weekly-summary-table td {{ border: 1px solid #dcdde1; padding: 6px 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .weekly-summary-table th {{ background-color: #e8f0fe; color: #1a73e8; }}
    .weekly-hours {{ font-weight: bold; color: #2c3e50; background-color: #f1f3f5; }}
    .weekly-label {{ font-weight: bold; background-color: #f8f9fa; color: #31333F; }}
    
    @media (max-width: 768px) {{
        .weekly-summary-table {{ font-size: 2.3vw !important; }}
        .weekly-summary-table th, .weekly-summary-table td {{ padding: 3px 1px !important; }}
    }}
</style>
"""
custom_css = custom_css.replace("__OY_FONT_FACES__", OY_FONT_FACES)
custom_css = "\n".join(l for l in _re.sub(r"/\*.*?\*/", "", custom_css, flags=_re.S).splitlines() if l.strip())
st.markdown(custom_css, unsafe_allow_html=True)

# ⭐️ 상단 바: 로고 · 프로그램 이름 (로그인하면 오른쪽에 로그아웃)
def _do_logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None

# ⭐️ Streamlit Cloud 오른쪽 아래 'Hosted with Streamlit' / 'Manage app' 버튼 숨기기
#    (버튼이 앱 바깥 페이지에 있어 CSS로는 안 됨 → 바깥 페이지에 숨김 스타일을 넣는 작은 스크립트.
#     Streamlit 공식 기능이 아니라 Cloud가 바뀌면 다시 보일 수 있음. 실패해도 앱 동작에는 영향 없음)
_HIDE_BADGE_JS = """
<script>
(function () {
  var css = '[class*="viewerBadge"],[class*="ViewerBadge"],[data-testid="appCreatorAvatar"],' +
            '[class*="_profileContainer"],[class*="_profilePreview"],[data-testid="manage-app-button"],' +
            'a[href*="streamlit.io/cloud"]{display:none !important;}';
  function docs() {
    var out = [], w = window;
    for (var i = 0; i < 5; i++) {
      try { w = w.parent; if (w && w.document && out.indexOf(w.document) < 0) out.push(w.document); } catch (e) { break; }
    }
    return out;
  }
  function run() {
    docs().forEach(function (d) {
      try {
        if (!d.getElementById('oy-hide-badge')) {
          var s = d.createElement('style'); s.id = 'oy-hide-badge'; s.textContent = css; (d.head || d.documentElement).appendChild(s);
        }
        // streamlit.io 로 가는 링크가 들어 있는 '화면에 고정된' 버튼 묶음만 숨김
        d.querySelectorAll('a[href*="streamlit.io"]').forEach(function (a) {
          var el = a;
          for (var k = 0; k < 8 && el && el !== d.body; k++) {
            if (d.defaultView.getComputedStyle(el).position === 'fixed') { el.style.setProperty('display', 'none', 'important'); break; }
            el = el.parentElement;
          }
        });
      } catch (e) {}
    });
  }
  run();
  var n = 0, t = setInterval(function () { run(); if (++n > 60) clearInterval(t); }, 500);
})();
</script>
"""

def _hide_cloud_badge():
    with st.container(key="oy_hidebadge"):
        components.html(_HIDE_BADGE_JS, height=0)

def render_topbar(show_logout=False):
    _lg = _logo_b64()
    _logo_html = (f"<img src='data:image/png;base64,{_lg}'>" if _lg
                  else "<div class='mark'><span class='material-symbols-outlined'>domain</span></div>")
    with st.container(key="topbar"):
        _c1, _c2 = st.columns([1, 0.2], vertical_alignment="center")
        _c1.markdown(f"<div class='oy-brand'>{_logo_html}<div class='t1'>T/S 근무 관리</div><span class='sub'>Created by tskwon</span></div>",
                     unsafe_allow_html=True)
        if show_logout:
            _c2.button("로그아웃", key="topbar_logout", icon=":material/logout:", on_click=_do_logout)
    _hide_cloud_badge()

def get_daily_password(date_str):
    random.seed(date_str + "_TS_TEAM_SECRET")
    pw = str(random.randint(1000, 9999))
    random.seed() 
    return pw

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


# --- 5. 세션 상태 관리 (로그인 처리) ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_user" not in st.session_state: st.session_state.current_user = None
if "login_selected_user" not in st.session_state: st.session_state.login_selected_user = ALL_USERS[0]

# 🔒 로그인 화면
if not st.session_state.logged_in:
    render_topbar(show_logout=False)
    
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
            pin_input = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력 ")
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True, icon=":material/login:")
            
            if submitted:
                # 💡 공통 비밀번호 5050 적용 (시트 호출이 없어 즉시 로그인됨)
                if pin_input == "5050":
                    st.session_state.logged_in = True
                    st.session_state.current_user = st.session_state.login_selected_user
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.", icon=":material/error:")
    st.stop() 


# =====================================================================
# 로그인 성공 시 메인 화면
# =====================================================================

# 💡 렉 개선의 핵심: 데이터를 캐싱하여 불필요한 구글 스프레드시트 통신을 막습니다.
@st.cache_data(ttl=300) # 5분(300초) 동안 캐시 유지 (다른 사람이 수정한 내용 갱신 목적)
def load_sheet_data():
    return sheet.get_all_values()

with st.spinner("데이터를 불러오는 중입니다..."):
    all_data = load_sheet_data()

# ⭐️ 상단 바 (로고 · 프로그램 이름 · 로그아웃)
render_topbar(show_logout=True)


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
                        
                        # 💡 데이터베이스가 변경되었으므로 캐시를 지우고 새로고침
                        load_sheet_data.clear()
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
                        
                        # 💡 캐시 지우기 추가
                        load_sheet_data.clear()
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
                        
                        # 💡 캐시 지우기 추가
                        load_sheet_data.clear()
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
                        
                        # 💡 캐시 지우기 추가
                        load_sheet_data.clear()
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