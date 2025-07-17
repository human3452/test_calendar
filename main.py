import os
import json
import datetime
import requests

from google.oauth2 import service_account
from googleapiclient.discovery import build

# 환경변수 로드
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
GOOGLE_CREDENTIALS_PATH = "credentials.json"

# Notion API 헤더 설정
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Google Calendar API 클라이언트 생성
def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"]
    )
    service = build("calendar", "v3", credentials=creds)
    return service

# 오늘~내일 일정 가져오기
def fetch_calendar_events():
    service = get_calendar_service()
    now = datetime.datetime.utcnow().isoformat() + "Z"
    tomorrow = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        timeMax=tomorrow,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events_result.get('items', [])

# Notion에 일정 추가
def add_event_to_notion(summary, start_date):
    data = {
        "parent": { "database_id": DATABASE_ID },
        "properties": {
            "이름": {
                "title": [{
                    "text": { "content": summary }
                }]
            },
            "진행일": {
                "date": {
                    "start": start_date
                }
            }
        }
    }

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers,
        data=json.dumps(data)
    )

    if response.status_code != 200:
        print(f"❌ Notion 등록 실패: {response.text}")
    else:
        print(f"✅ Notion 등록 성공: {summary} / {start_date}")

# 메인 로직 실행
if __name__ == "__main__":
    print("📆 Google Calendar 일정 가져오는 중...")
    events = fetch_calendar_events()

    if not events:
        print("⚠️ 등록할 일정이 없습니다.")
    else:
        for event in events:
            summary = event.get('summary', '제목 없음')
            start = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            if summary and start:
                add_event_to_notion(summary, start)
