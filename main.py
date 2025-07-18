import os
import json
import datetime
import requests

from google.oauth2 import service_account
from googleapiclient.discovery import build

# 환경변수
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
GOOGLE_CREDENTIALS_PATH = "credentials.json"
CALENDAR_ID = "human646581@gmail.com"

# Notion API 헤더
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Google Calendar API 클라이언트
def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"]
    )
    return build("calendar", "v3", credentials=creds)

# 이번 달 1일부터 말일까지 일정 가져오기
def fetch_calendar_events():
    service = get_calendar_service()

    KST = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(tz=KST)

    start_of_month = now.replace(day=1)
    if now.month == 12:
        start_of_next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        start_of_next_month = now.replace(month=now.month + 1, day=1)

    time_min = start_of_month.isoformat()
    time_max = start_of_next_month.isoformat()

    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events_result.get('items', [])

# Notion DB에 이미 등록된 event_id인지 확인
def is_duplicate_event(event_id):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "event_id",
            "rich_text": {
                "equals": event_id
            }
        }
    }
    res = requests.post(url, headers=headers, data=json.dumps(payload))
    results = res.json().get("results", [])
    return len(results) > 0

# Notion에 일정 추가
def add_event_to_notion(summary, start_date, event_id):
    if is_duplicate_event(event_id):
        print(f"⏩ 중복 이벤트 건너뜀: {summary}")
        return

    data = {
        "parent": { "database_id": DATABASE_ID },
        "properties": {
            "이름": {
                "title": [{ "text": { "content": summary } }]
            },
            "진행일": {
                "date": { "start": start_date }
            },
            "event_id": {
                "rich_text": [{ "text": { "content": event_id } }]
            }
        }
    }

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers,
        data=json.dumps(data)
    )

    if response.status_code == 200:
        print(f"✅ 등록됨: {summary}")
    else:
        print(f"❌ 등록 실패: {summary} / {response.status_code} - {response.text}")

# 실행
if __name__ == "__main__":
    print("📅 이번 달 Google Calendar 일정 가져오는 중...")
    events = fetch_calendar_events()

    if not events:
        print("⚠️ 등록할 일정이 없습니다.")
    else:
        for event in events:
            summary = event.get("summary", "제목 없음")
            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            event_id = event.get("id")

            if summary and start and event_id:
                add_event_to_notion(summary, start, event_id)
