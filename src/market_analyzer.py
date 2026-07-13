import os
import json
import re
from googleapiclient.discovery import build
from google.genai import types
from dotenv import load_dotenv
from .topic_recommender import _get_client, _generate, MODEL_FLASH, MODEL_PRO

class MarketAnalyzer:
    def __init__(self, api_key=None):
        load_dotenv()
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.youtube = None
        if self.api_key:
            try:
                # API 키가 있을 때만 유튜브 클라이언트 빌드
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            except Exception as e:
                print(f"[MarketAnalyzer] YouTube API client build failed: {e}")
        else:
            print("[MarketAnalyzer] ⚠️ YOUTUBE_API_KEY or GOOGLE_API_KEY not found. Falling back to mock stats mode.")
        self.genai_client = _get_client()

    def search_competitors(self, query: str, max_results: int = 20):
        """주제와 관련된 경쟁 채널 및 영상 검색"""
        if not self.youtube:
            print("[MarketAnalyzer] ⚠️ YouTube API client is not initialized due to missing API Key.")
            return []
        try:
            search_response = self.youtube.search().list(
                q=query,
                part='snippet',
                maxResults=max_results,
                type='video',
                order='viewCount'
            ).execute()

            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            if not video_ids: return []

            stats_response = self.youtube.videos().list(
                part='statistics,snippet,topicDetails',
                id=','.join(video_ids)
            ).execute()

            results = []
            for item in stats_response.get('items', []):
                snippet = item['snippet']
                stats = item['statistics']
                view_count = int(stats.get('viewCount', 0))
                like_count = int(stats.get('likeCount', 0))

                # 사용자가 요청한 고품질 필터링 (좋아요 1만 이상 또는 조회수 1만 이상)
                if view_count >= 10000 or like_count >= 10000:
                    results.append({
                        'video_id': item['id'],
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'channel_title': snippet['channelTitle'],
                        'view_count': view_count,
                        'like_count': like_count,
                        'tags': snippet.get('tags', []),
                        'published_at': snippet['publishedAt']
                    })
            return results
        except Exception as e:
            print(f"Market analysis search failed: {e}")
            return []

    def analyze_market_patterns(self, competitive_data: list):
        """Gemini를 사용한 성공 패턴 분석"""
        if not competitive_data: return "분석할 데이터가 부족합니다."
        data_summary = json.dumps(competitive_data, ensure_ascii=False, indent=2)
        prompt = f"""
당신은 최고의 유튜브 성장 전략가입니다. 아래 데이터를 분석하여 '성공 공식'을 도출해 주세요.
[경쟁 데이터]
{data_summary}
[분석 요청 사항]
1. 제목 스타일 및 클릭률 유도 요소
2. 시청자 이탈 방지 타이밍 및 영상 구조 분석
3. SEO 세팅 100점을 위한 핵심 태그 및 설명란 패턴
4. 반응 좋았던 키워드 TOP 5
5. 썸네일 및 훅(Hook)에서 공통적으로 발견되는 패턴 분석
"""
        analysis = _generate(self.genai_client, prompt, model_name=MODEL_PRO)
        intel_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'market_intelligence.json')
        os.makedirs(os.path.dirname(intel_path), exist_ok=True)
        with open(intel_path, 'w', encoding='utf-8') as f:
            json.dump({"raw_data": competitive_data, "analysis": analysis}, f, ensure_ascii=False, indent=2)
        return analysis

    def get_market_intelligence(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'market_intelligence.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        return None
