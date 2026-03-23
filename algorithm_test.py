import os
import random
import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=API_KEY)


# ── 1. 영상 ID 리스트 확보 (search.list) ──────────────────────────
def search_video_ids(query: str, max_results: int = 20) -> list[str]:
    request = youtube.search().list(
        part="id",
        q=query,
        type="video",
        maxResults=max_results,
        relevanceLanguage="ko"
    )
    response = request.execute()
    return [item["id"]["videoId"] for item in response["items"]]


# ── 2. 영상 통계 + snippet (videos.list) ─────────────────────────
def get_video_stats(video_ids: list[str]) -> list[dict]:
    # videos.list는 한 번에 최대 50개
    chunks = [video_ids[i:i+50] for i in range(0, len(video_ids), 50)]
    videos = []

    for chunk in chunks:
        request = youtube.videos().list(
            part="statistics,snippet",
            id=",".join(chunk)
        )
        response = request.execute()
        for item in response["items"]:
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            videos.append({
                "video_id":     item["id"],
                "title":        snippet.get("title", ""),
                "channel_id":   snippet.get("channelId", ""),
                "channel_name": snippet.get("channelTitle", ""),
                "view_count":   int(stats.get("viewCount", 0)),
                "like_count":   int(stats.get("likeCount", 0)),
            })
    return videos


# ── 3. 채널 구독자 수 (channels.list) ────────────────────────────
def get_subscriber_counts(channel_ids: list[str]) -> dict[str, int]:
    unique_ids = list(set(channel_ids))
    chunks = [unique_ids[i:i+50] for i in range(0, len(unique_ids), 50)]
    sub_map = {}

    for chunk in chunks:
        request = youtube.channels().list(
            part="statistics",
            id=",".join(chunk)
        )
        response = request.execute()
        for item in response["items"]:
            sub_map[item["id"]] = int(
                item["statistics"].get("subscriberCount", 0)
            )
    return sub_map


# ── 4. 테이블 구성 ────────────────────────────────────────────────
def build_video_table(query: str, max_results: int = 20) -> pd.DataFrame:
    video_ids = search_video_ids(query, max_results)
    videos    = get_video_stats(video_ids)

    channel_ids   = [v["channel_id"] for v in videos]
    sub_map       = get_subscriber_counts(channel_ids)

    for v in videos:
        v["subscriber_count"] = sub_map.get(v["channel_id"], 0)

    return pd.DataFrame(videos)


# ── 5. 랜덤 나열 ─────────────────────────────────────────────────
def shuffle_random(df: pd.DataFrame) -> pd.DataFrame:
    """단순 셔플"""
    return df.sample(frac=1).reset_index(drop=True)


def shuffle_weighted(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    조회수 / 구독자수 비율로 가중치 산출
    → 구독자 대비 조회수가 높을수록 더 자주 선택됨
    """
    df = df.copy()
    df["weight"] = df.apply(
        lambda r: r["view_count"] / r["subscriber_count"]
        if r["subscriber_count"] > 0 else 0,
        axis=1
    )
    total = df["weight"].sum()
    if total == 0:
        return shuffle_random(df)

    df["prob"] = df["weight"] / total
    sampled = df.sample(n=min(top_n, len(df)), weights="prob", replace=False)
    return sampled.reset_index(drop=True)


# ── 실행 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    query = "아이폰 16 리뷰"

    df = build_video_table(query, max_results=20)
    print("=== 전체 영상 테이블 ===")
    print(df[["title", "view_count", "like_count", "subscriber_count"]])

    print("\n=== 단순 랜덤 ===")
    print(shuffle_random(df)[["title", "view_count"]].head(5))

    print("\n=== 가중치 기반 랜덤 (조회수/구독자수) ===")
    print(shuffle_weighted(df, top_n=5)[["title", "view_count", "subscriber_count", "prob"]])