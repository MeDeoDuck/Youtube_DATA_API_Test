from googleapiclient.discovery import build

# 코드에서 불러올 때
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=API_KEY)

# 테스트: 아이폰 16 리뷰 영상 검색
request = youtube.search().list(
    part="snippet",
    q="아이폰 16 리뷰",
    type="video",
    maxResults=5
)
response = request.execute()

for item in response["items"]:
    print(item["snippet"]["title"])