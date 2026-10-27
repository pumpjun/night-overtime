"""구글 시트의 지난 야근 기록을 Firebase(Firestore)로 옮기는 프로그램 (한 번만 실행)

실행: 야근계획_Firebase 폴더에서  python migrate_to_firebase.py

- 먼저 구글 시트 전체를 CSV로 백업(시트백업_날짜.csv)한 뒤, 몇 건을 옮길지 보여주고 물어봅니다.
- 같은 사람 · 같은 날 · 같은 구분은 문서 하나로 저장되므로, 여러 번 실행해도 중복이 생기지 않습니다.
  (전환 전후로 시트에만 들어간 기록이 있으면 한 번 더 실행하면 채워집니다)
- 구글 시트는 지우거나 고치지 않습니다. 읽기만 합니다.

필요한 것
  .streamlit/secrets.toml 의 gcp_service_account  (지금 쓰는 구글 시트 키)
  firebase_key.json  (이 폴더)  또는 secrets.toml 의 firebase_service_account
"""
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))
COLLECTION = "ts_work_plans"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1v4REfMtoTB9CQzBRks45UpaVmptHxYD-mYeAOnavDvY/edit?gid=0#gid=0"


def load_secrets():
    p = os.path.join(HERE, ".streamlit", "secrets.toml")
    if not os.path.isfile(p):
        return {}
    try:
        import tomllib
        with open(p, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        import toml
        return toml.load(p)


def as_json(v):
    return json.loads(v) if isinstance(v, str) else dict(v)


def firebase_info(secrets):
    if "firebase_service_account" in secrets:
        return as_json(secrets["firebase_service_account"])
    for p in (os.environ.get("OY_FIREBASE_KEY", ""), os.path.join(HERE, "firebase_key.json"),
              os.path.join(os.path.dirname(HERE), "firebase_key.json")):
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return None


def get_work_type(row):
    if len(row) >= 6 and str(row[5]).strip():
        return str(row[5]).strip()
    if len(row) >= 4 and row[3] in ("12:00", "17:00"):
        return "휴일"
    return "야간"


def main():
    yes = "--yes" in sys.argv
    secrets = load_secrets()
    if "gcp_service_account" not in secrets:
        sys.exit("✖ .streamlit/secrets.toml 에서 gcp_service_account 를 찾지 못했습니다.")
    fb = firebase_info(secrets)
    if not fb:
        sys.exit("✖ Firebase 키(firebase_key.json)를 찾지 못했습니다. 이 폴더에 넣고 다시 실행해 주세요.")

    import gspread
    from google.cloud import firestore
    from google.oauth2.service_account import Credentials

    # 1) 시트 읽기 + 백업
    print("구글 시트를 읽는 중...")
    gcreds = Credentials.from_service_account_info(
        as_json(secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    values = gspread.authorize(gcreds).open_by_url(SHEET_URL).sheet1.get_all_values()
    stamp = datetime.now(KST).strftime("%Y%m%d_%H%M")
    backup = os.path.join(HERE, f"시트백업_{stamp}.csv")
    with open(backup, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(values)
    print(f"  · 백업 저장: {backup}")

    # 2) 정리
    docs, skipped, dup = {}, [], 0
    for i, r in enumerate(values[1:], start=2):
        r = [str(c).strip() for c in r] + ["", "", "", ""]
        if not r[1] and not r[2]:
            continue  # 빈 줄
        if not r[1] or not r[2] or not r[3]:
            skipped.append((i, r[:6]))
            continue
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                r[2] = datetime.strptime(r[2], fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                pass
        else:
            skipped.append((i, r[:6]))
            continue
        wt = get_work_type(r)
        did = f"{r[2]}_{wt}_{r[1]}"
        if did in docs:
            dup += 1  # 같은 사람·날·구분이 두 줄 → 아래쪽(나중) 줄로
        docs[did] = {"name": r[1], "date": r[2], "type": wt, "end": r[3],
                     "reason": r[4] if len(r) > 4 else "", "legacy_id": r[0],
                     "migrated_at": datetime.now(KST).isoformat(timespec="seconds")}

    dates = sorted(d["date"] for d in docs.values())
    by_type = Counter(d["type"] for d in docs.values())
    print(f"\n시트 기록 {len(values) - 1}줄 → 옮길 기록 {len(docs)}건")
    if dates:
        print(f"  · 기간: {dates[0]} ~ {dates[-1]}")
    print("  · " + ", ".join(f"{k} {v}건" for k, v in by_type.items()))
    if dup:
        print(f"  · 같은 사람·날·구분이 겹친 줄 {dup}개 → 아래쪽 줄 내용으로 합침")
    if skipped:
        print(f"  · 날짜/이름이 비었거나 형식이 달라 건너뛴 줄 {len(skipped)}개:")
        for i, r in skipped[:10]:
            print(f"      {i}행: {r}")

    db = firestore.Client(project=fb["project_id"], credentials=Credentials.from_service_account_info(fb))
    print(f"\nFirebase 프로젝트: {fb['project_id']}  /  컬렉션: {COLLECTION}")
    if not yes and input("옮길까요? (y/n) ").strip().lower() != "y":
        print("취소했습니다.")
        return

    # 3) 쓰기 (400건씩 묶어서)
    items = list(docs.items())
    for k in range(0, len(items), 400):
        batch = db.batch()
        for did, data in items[k:k + 400]:
            batch.set(db.collection(COLLECTION).document(did), data, merge=True)
        batch.commit()
        print(f"  · {min(k + 400, len(items))}/{len(items)} 저장")

    # 4) 확인: 옮긴 문서를 다시 읽어 내용 비교
    print("\n확인 중...")
    stored = {d.id: d.to_dict() for d in db.collection(COLLECTION).stream()}
    bad = [did for did, data in docs.items()
           if did not in stored or any(stored[did].get(f) != data[f] for f in ("name", "date", "type", "end", "reason"))]
    if bad:
        print(f"✖ {len(bad)}건이 다릅니다: {bad[:10]}")
    else:
        print(f"✔ {len(docs)}건 모두 확인 완료 (Firebase 전체 {len(stored)}건)")


if __name__ == "__main__":
    main()
