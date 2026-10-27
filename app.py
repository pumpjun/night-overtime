import streamlit as st
import streamlit.components.v1 as components

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


# ⭐️ 2. 사용자 · 데이터 (명단은 ot_page.py, 저장은 ot_store.py — 통합 프로그램과 같은 파일)
import ot_page

members, admins, ALL_USERS = ot_page.members, ot_page.admins, ot_page.ALL_USERS

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
# 로그인 성공 시 메인 화면 (통합 프로그램과 같은 화면 코드)
# =====================================================================
render_topbar(show_logout=True)
ot_page.main(font_faces=OY_FONT_FACES)
