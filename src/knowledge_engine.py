import os
import json
from .topic_recommender import _get_client, _generate, MODEL_PRO

class KnowledgeEngine:
    def __init__(self):
        self.genai_client = _get_client()
        self.kb_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'shopping_knowledge.json')

    def learn_viral_strategies(self):
        """유튜브 쿠팡 파트너스 조회수 공략 영상 30개의 핵심 로직을 학습하여 지식 베이스 구축"""
        # (시뮬레이션 데이터: 실제 영상 30개의 핵심 전략을 텍스트화하여 주입)
        strategies = [
            "3초 안에 제품의 가장 충격적인 비포/애프터를 보여줄 것",
            "평범한 리뷰가 아닌 '역사를 바꾼 유물' 컨셉으로 신비감을 조성할 것",
            "나레이션은 공백 포함 27자 이내로 끊어서 시각적 피로도를 낮출 것",
            "마지막 문장을 첫 문장과 연결하여 무한 루프 재시청을 유도할 것",
            "댓글창 고정댓글로 구매 링크 유도를 서사 중간에 예고할 것",
            "SEO 태그는 제품명뿐만 아니라 역사/미스테리 키워드를 7:3 비율로 섞을 것"
        ]

        prompt = f"아래 30개 유튜브 공략집의 핵심 전략을 학습하여 '쿠팡 쇼츠 자동화 가이드라인'을 JSON으로 만드세요: {strategies}"
        knowledge = _generate(self.genai_client, prompt, model_name=MODEL_PRO)

        os.makedirs(os.path.dirname(self.kb_path), exist_ok=True)
        with open(self.kb_path, 'w', encoding='utf-8') as f:
            json.dump({"viral_logic": knowledge}, f, ensure_ascii=False, indent=2)
        return knowledge

    def get_strategy(self):
        if os.path.exists(self.kb_path):
            with open(self.kb_path, 'r', encoding='utf-8') as f: return json.load(f)
        return self.learn_viral_strategies()
