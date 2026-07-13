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
유튜브 SEO 마스터로서 아래 영상의 메타데이터를 100점 기준으로 최적화하세요.
[시장 분석 정보] {market_context}
[현재 메타데이터] 제목: {current_title}, 설명: {current_description}, 태그: {', '.join(current_tags)}
[지침]
1. 제목 앞쪽 35%에 핵심 키워드 배치
2. 제목, 설명, 태그 모두에 포함되는 트리플 키워드 매칭
3. 설명란 시작 150자 이내 키워드 반복
반드시 JSON(title, description, tags) 형식으로만 반환하세요.
"""
        optimized_json = _generate(self.genai_client, prompt, model_name=MODEL_PRO)
        try:
            start_idx = optimized_json.find('{')
            end_idx = optimized_json.rfind('}') + 1
            return json.loads(optimized_json[start_idx:end_idx])
        except: return None

    def revive_stalled_video(self, video_id: str, stats: dict, channel_stats: dict = None):
        """조회수가 멈춘 기존 영상을 살리기 위한 알고리즘 분석 및 심폐소생 리포트 생성"""
        avg_views = channel_stats.get('avg_views', 1000) if channel_stats else 1000
        current_views = int(stats.get('viewCount', 0))

        prompt = f"""
유튜브 알고리즘 전문가로서, 조회수가 멈춘 영상(ID: {video_id})의 심폐소생 가능성을 분석하세요.
[데이터] 현재 조회수: {current_views}, 채널평균: {avg_views}, 지난 48h 조회수: {stats.get('recent_views', '0')}

분석 목표:
1. SEO 점수 100점 달성 전략
2. 알고리즘 활성도 100% 강제 도달 방법
3. 소생 후 예상 알고리즘 지표 산출

응답을 반드시 아래 JSON 형식으로 반환하세요:
{{
  "success_rate": 98,
  "expected_views_48h": {int(avg_views * 1.5)},
  "success_reasons": ["알고리즘 시그널 재점화 가능성", "키워드 트래픽 급증", "시청자 재유입 최적화"],
  "failure_reasons": ["썸네일 교체 지연", "초반 3초 이탈 리스크", "경쟁 채널 실시간 모니터링 필요"],
  "algorithm_activity": 100,
  "predicted_graph_data": [10, 50, 200, 800, 1500, 1200, 800, 400],
  "action_plan": "vidIQ 100점 메타데이터를 즉시 적용하고, 썸네일의 색 대비를 30% 높이세요."
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
                "predicted_graph_data": [5, 10, 15, 20, 25, 20, 15, 10],
                "action_plan": "분석에 실패했습니다. 수동으로 메타데이터를 점검하세요."
            }
