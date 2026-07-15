import os
import json
from .seo_analyzer import SEOAnalyzer
from .topic_recommender import _get_client, _generate, MODEL_PRO
from .market_analyzer import MarketAnalyzer

class ChannelOptimizer:
    def __init__(self):
        self.genai_client = _get_client()
        self.market_analyzer = MarketAnalyzer()

    def optimize_video_metadata(self, current_title: str, current_description: str, current_tags: list):
        """기존 영상의 메타데이터를 SEO 100점에 가깝게 최적화"""
        market_intel = self.market_analyzer.get_market_intelligence()
        market_context = market_intel.get("analysis", "") if market_intel else "성공적인 패턴을 따르세요."
        prompt = f"""
당신은 유튜브 SEO 마스터이자 평행/대체역사 다큐멘터리 전문 PD입니다.
[채널 주제 제약사항]
우리 채널은 "평행 세계", "대체 역사", "국뽕 역사 다큐멘터리"가 절대 정체성입니다.
어떤 카테고리의 상품(드라이기, RC카, 캠핑 텐트 등)이 엮여 있더라도, 반드시 역사적 서사("승리", "정복", "해방", "위기 극복" 등)가 부각되는 웅장한 대체역사 스타일의 제목과 설명이어야 합니다. 요리 요리법 등의 다른 주제로 이탈하면 안 됩니다.

[시장 분석 정보] {market_context}
[현재 메타데이터] 제목: {current_title}, 설명: {current_description}, 태그: {', '.join(current_tags)}
[지침]
1. 제목 앞쪽 35%에 핵심 키워드 배치
2. 제목, 설명, 태그 모두에 포함되는 트리플 키워드 매칭
3. 설명란 시작 150자 이내 키워드 반복
4. 자극적이고 클릭률을 높이는 대체역사 What If 의문형/반전 유도 제목 권장
반드시 JSON(title, description, tags) 형식으로만 반환하세요.
"""
        optimized_json = _generate(self.genai_client, prompt, model_name=MODEL_PRO)
        try:
            start_idx = optimized_json.find('{')
            end_idx = optimized_json.rfind('}') + 1
            return json.loads(optimized_json[start_idx:end_idx])
        except: return None

    def revive_stalled_video(self, video_id: str, stats: dict, channel_stats: dict = None, current_title: str = "", current_description: str = ""):
        """조회수가 멈춘 기존 영상을 살리기 위한 알고리즘 분석 및 심폐소생 리포트 생성"""
        avg_views = channel_stats.get('avg_views', 1000) if channel_stats else 1000
        current_views = int(stats.get('viewCount', 0))

        prompt = f"""
당신은 유튜브 알고리즘 전문가이자 평행/대체역사 다큐멘터리 전문 PD입니다.
48시간 동안 조회수가 멈추거나 정체된 쇼츠(또는 롱폼) 영상(ID: {video_id})의 심폐소생 가능성을 분석하세요.

[현재 영상 정보]
- 제목: {current_title}
- 설명: {current_description}
- 현재 조회수: {current_views}
- 채널 평균 조회수: {avg_views}
- 지난 48h 조회수: {stats.get('recent_views', '0')}

[채널 주제 제약사항]
우리 채널은 "평행 세계", "대체 역사", "국뽕 역사 다큐멘터리"가 절대 정체성입니다.
소생할 때에도 반드시 국뽕 대체 역사 서사(승리, 정복, 해방)의 기조를 유지하면서 최적의 vidIQ 100점 메타데이터를 갖추도록 분석해야 합니다.

분석 목표:
1. SEO 점수 100점 달성 전략
2. 알고리즘 활성도 100% 강제 도달 방법
3. 시청자 유지율(Retention) 이탈 방지 분석: 
   - 특히 시청자 이탈이 가장 빈번한 **이탈 시점인 씬 2번~3번(재생 4초~9초 부근)에 2번~3번의 강력한 후킹 자극(기습적 질문 던지기, 예측 불가능한 대체역사적 사실 폭로 등)**을 믹싱 및 대본에 추가하는 공략을 'action_plan'에 명시하세요.
4. 분석 기반 최적화 장면당 시간초(recommended_duration) 산출 (1~30초 범위 정수)

응답을 반드시 아래 JSON 형식으로 반환하세요:
{{
  "success_rate": 98,
  "expected_views_48h": {int(avg_views * 1.5)},
  "success_reasons": ["대체 역사 키워드 알고리즘 시그널 재점화", "국뽕 역사 트래픽 급증", "시청자 재유입 최적화"],
  "failure_reasons": ["역사적 썸네일 교체 지연", "초반 3초 대체역사 훅 이탈 리스크"],
  "algorithm_activity": 100,
  "recommended_duration": 4,
  "predicted_graph_data": [10, 50, 200, 800, 1500, 1200, 800, 400],
  "action_plan": "평행세계 다큐의 비장함을 담은 썸네일로 교체하고, 이탈이 발생하는 씬 2~3번에 2~3회 연속적인 역사 반전 후킹 질문을 주입하세요. 장면 시간초는 4초가 최적입니다."
}}
"""
        response = _generate(self.genai_client, prompt, model_name=MODEL_PRO)
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            return json.loads(response[start_idx:end_idx])
        except:
            return {
                "success_rate": 50, "expected_views_48h": avg_views,
                "success_reasons": ["데이터 분석 불가", "기존 데이터 기반", "유입 가능성 존재"],
                "failure_reasons": ["데이터 부족", "알고리즘 정체", "노출 부족"],
                "algorithm_activity": 30,
                "recommended_duration": 3,
                "predicted_graph_data": [5, 10, 15, 20, 25, 20, 15, 10],
                "action_plan": "분석에 실패했습니다. 이탈 구간(씬 2~3번)에 2~3회 연속 후킹을 반영하고 수동으로 메타데이터를 점검하세요."
            }

    def _parse_iso8601_duration(self, duration_str: str) -> int:
        """ISO 8601 duration format (e.g. PT15S, PT1M5S)을 초 단위 정수로 변환"""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0
        return hours * 3600 + minutes * 60 + seconds

    def get_optimal_shorts_length(self) -> int:
        """유튜브 채널의 최근 숏폼 성과를 분석하여 최적의 Shorts 길이를 반환"""
        try:
            from .youtube_uploader import YouTubeUploader
            uploader = YouTubeUploader()
            if os.path.exists(uploader.credentials_pickle):
                uploader.authenticate()
                client = uploader.youtube_client
                if client:
                    channels_response = client.channels().list(mine=True, part='contentDetails').execute()
                    if channels_response.get('items'):
                        uploads_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                        playlist_response = client.playlistItems().list(playlistId=uploads_id, part='snippet', maxResults=30).execute()
                        video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_response.get('items', [])]
                        if video_ids:
                            videos_response = client.videos().list(id=','.join(video_ids), part='contentDetails,statistics').execute()
                            shorts_durations = []
                            for item in videos_response.get('items', []):
                                duration_str = item['contentDetails']['duration']
                                seconds = self._parse_iso8601_duration(duration_str)
                                if 5 <= seconds <= 60:
                                    views = int(item['statistics'].get('viewCount', 0))
                                    shorts_durations.append((seconds, views))
                            if shorts_durations:
                                # 가장 높은 조회수의 Shorts 재생시간 반환
                                shorts_durations.sort(key=lambda x: x[1], reverse=True)
                                optimal_len = shorts_durations[0][0]
                                print(f"  [Optimizer] 📊 내 채널 분석 결과 최적 Shorts 재생시간은 '{optimal_len}초' 입니다. (최대 조회수: {shorts_durations[0][1]:,}회)")
                                return optimal_len
        except Exception as e:
            print(f"  [Optimizer] ⚠️ 유튜브 API 기반 최적 Shorts 분석 실패 ({e}). 기본값(12초)을 사용합니다.")
        return 12
