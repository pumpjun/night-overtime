"""야근계획 데이터 저장소 — Firebase(Firestore)가 원본, 구글 시트는 사본(백업)

★ 이 파일은 '야근계획_Firebase' 폴더(폰용 Streamlit Cloud 앱)와 '통합프로그램/views' 폴더에
   똑같은 내용으로 들어 있습니다. 고칠 때는 두 곳 모두 같은 파일로 바꿔 주세요.

동작
  - Firebase 키가 있으면: Firebase에서 읽고, 쓸 때는 Firebase + 구글 시트 둘 다 기록
  - Firebase 키가 없으면: 지금처럼 구글 시트만 사용 (키 설정 전에 배포해도 안전)

Firebase 키 찾는 순서
  1) Streamlit secrets 의 firebase_service_account  (Streamlit Cloud → 앱 Settings → Secrets)
  2) 환경변수 OY_FIREBASE_KEY 에 적힌 파일 경로
  3) 프로그램 폴더의 firebase_key.json  (야근계획_Firebase 폴더 / 통합프로그램 폴더에 각각 하나씩)
"""
import json
import os
from datetime import datetime, timedelta, timezone

import streamlit as st

KST = timezone(timedelta(hours=9))
COLLECTION = "ts_work_plans"  # Spectra50 데이터와 섞이지 않도록 이 컬렉션만 사용
SHEET_URL = "https://docs.google.com/spreadsheets/d/1v4REfMtoTB9CQzBRks45UpaVmptHxYD-mYeAOnavDvY/edit?gid=0#gid=0"
HEADER = ["ID", "이름", "날짜", "종료시간", "사유", "구분"]
_HERE = os.path.dirname(os.path.abspath(__file__))


def get_work_type(row):
    if len(row) >= 6 and str(row[5]).strip() != "":
        return str(row[5]).strip()
    if len(row) >= 4 and row[3] in ["12:00", "17:00"]:
        return "휴일"
    return "야간"


def doc_id(name, date_str, work_type):
    """같은 사람 · 같은 날 · 같은 구분은 문서 하나 → 다시 등록하면 '변경'이 되고 중복이 생기지 않음"""
    return f"{date_str}_{work_type}_{name}"


# ------------------------------------------------------------------ 연결
def _secret_json(key):
    try:
        v = st.secrets[key]
    except Exception:
        return None
    try:
        return json.loads(v) if isinstance(v, str) else dict(v)
    except Exception:
        return None


def _firebase_info():
    info = _secret_json("firebase_service_account")
    if info:
        return info
    paths = [os.environ.get("OY_FIREBASE_KEY", ""),
             os.path.join(_HERE, "firebase_key.json"),
             os.path.join(os.path.dirname(_HERE), "firebase_key.json"),
             os.path.join(os.getcwd(), "firebase_key.json")]
    for p in paths:
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return None


@st.cache_resource(show_spinner=False)
def _firestore():
    info = _firebase_info()
    if not info:
        return None
    from google.cloud import firestore
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_info(info)
    return firestore.Client(project=info["project_id"], credentials=creds)


@st.cache_resource(show_spinner=False)
def _sheet():
    info = _secret_json("gcp_service_account")
    if not info:
        return None
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds).open_by_url(SHEET_URL).sheet1


def backend():
    return "firebase" if _firestore() is not None else "sheets"


def status_text():
    if backend() == "firebase":
        return "저장소: Firebase" + (" · 구글 시트에 사본 기록" if _sheet() is not None else "")
    return "저장소: 구글 시트 (Firebase 키 없음)"


# ------------------------------------------------------------------ 읽기
@st.cache_data(ttl=300, show_spinner=False)
def load_data(start, end):
    """start~end(YYYY-MM-DD) 기록을 [머리글, [ID, 이름, 날짜, 종료, 사유, 구분], ...] 형태로.
    (기간을 정해서 읽어야 Firebase 무료 읽기 한도를 아낄 수 있음)"""
    db = _firestore()
    rows = []
    if db is not None:
        from google.cloud.firestore_v1.base_query import FieldFilter
        q = (db.collection(COLLECTION)
             .where(filter=FieldFilter("date", ">=", start))
             .where(filter=FieldFilter("date", "<=", end)))
        for d in q.stream():
            x = d.to_dict()
            rows.append([str(x.get("legacy_id") or d.id), x.get("name", ""), x.get("date", ""),
                         x.get("end", ""), x.get("reason", ""), x.get("type", "")])
        rows.sort(key=lambda r: (r[2], r[1]))
    else:
        sh = _sheet()
        if sh is None:
            raise RuntimeError("Firebase 키도, 구글 시트 키(gcp_service_account)도 찾지 못했습니다.")
        for r in sh.get_all_values()[1:]:
            if len(r) >= 4 and start <= r[2] <= end:
                r = (list(r) + ["", ""])[:6]
                r[5] = get_work_type(r)
                rows.append(r)
    return [HEADER] + rows


# ------------------------------------------------------------------ 쓰기
def _sheet_find(values, name, date_str, work_type):
    for i, row in enumerate(values):
        if i > 0 and len(row) >= 4 and row[1] == name and row[2] == date_str and get_work_type(row) == work_type:
            return i + 1  # 시트 행 번호 (1부터)
    return -1


def _sheet_save(name, date_str, work_type, end, reason):
    sh = _sheet()
    values = sh.get_all_values()
    r = _sheet_find(values, name, date_str, work_type)
    if r != -1:
        sh.update_cell(r, 4, end)
        sh.update_cell(r, 5, reason)
        sh.update_cell(r, 6, work_type)
        return "변경"
    sh.append_row([len(values), name, date_str, end, reason, work_type])
    return "등록"


def _sheet_delete(name, date_str, work_type):
    sh = _sheet()
    r = _sheet_find(sh.get_all_values(), name, date_str, work_type)
    if r != -1:
        sh.delete_rows(r)
        return True
    return False


def _mirror(fn, *a):
    """Firebase에 저장한 뒤 구글 시트 사본 기록 (실패해도 Firebase 기록은 그대로)"""
    if _sheet() is None:
        return
    try:
        fn(*a)
    except Exception:
        st.toast("구글 시트 사본 기록에 실패했습니다. (Firebase에는 저장됨)", icon=":material/warning:")


def save(name, date_str, work_type, end, reason):
    """등록 또는 수정 → '등록' / '변경'"""
    db = _firestore()
    if db is None:
        res = _sheet_save(name, date_str, work_type, end, reason)
    else:
        ref = db.collection(COLLECTION).document(doc_id(name, date_str, work_type))
        exists = ref.get().exists
        now = datetime.now(KST).isoformat(timespec="seconds")
        data = {"name": name, "date": date_str, "type": work_type, "end": end, "reason": reason, "updated_at": now}
        if not exists:
            data["created_at"] = now
        ref.set(data, merge=True)
        res = "변경" if exists else "등록"
        _mirror(_sheet_save, name, date_str, work_type, end, reason)
    load_data.clear()
    return res


def delete(name, date_str, work_type):
    """취소 → 지운 기록이 있었으면 True"""
    db = _firestore()
    if db is None:
        found = _sheet_delete(name, date_str, work_type)
    else:
        ref = db.collection(COLLECTION).document(doc_id(name, date_str, work_type))
        found = ref.get().exists
        if found:
            ref.delete()
        _mirror(_sheet_delete, name, date_str, work_type)
    load_data.clear()
    return found
