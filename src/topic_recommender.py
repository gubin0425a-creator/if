"""
topic_recommender.py
────────────────────
v10.2 지능형 하이브리드 엔진:
  - 주제 입력 없이도 트렌드 기반 소주제 추천
  - AI 분석 기반 예상 조회수(10,000+) 산출 로직
  - 숏폼(4컷) / 롱폼(24컷) / 쿠팡 바이럴(30컷) 모드 통합 지원
  - [27자의 법칙] 및 [SEO 100점] 강제 적용
"""
import os
import sys
import json
import re
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MODEL_PRO = "gemini-2.5-pro"
MODEL_FLASH = "gemini-2.5-flash"

LANGUAGES = {"ko": "한국어", "en": "English", "ja": "日本語"}
TTS_VOICES = {"ko": "ko-KR-InJoonNeural", "en": "en-US-GuyNeural", "ja": "ja-JP-KeitaNeural"}

class TopicRecommendation(BaseModel):
    index: int = Field(description="1~5")
    title: str = Field(description="What If 제목")
    hook: str = Field(description="3초 이탈 방지 훅")
    predicted_views: int = Field(description="예상 조회수 (알고리즘 분석치, 최소 10,000 이상)")

class TopicRecommendations(BaseModel):
    topics: List[TopicRecommendation]

class Scene(BaseModel):
    scene_num: int
    narration: str = Field(description="반드시 공백 포함 27자 이내!!")
    subtitle: str = Field(description="반드시 공백 포함 27자 이내!!")
    image_query: str = Field(description="위키미디어(Wikimedia Commons) 실제 고증 이미지 검색용 1~3단어 영문 핵심 키워드 (예: 'Kim Ju-ae', 'North Korea map', 'Kim Jong-un')")
    video_query: str = Field(description="스톡 비디오 사이트 검색용 1~3단어 영문 핵심 키워드 (예: 'North Korea military', 'Pyongyang street')")
    ai_prompt: str = Field(description="AI 이미지/비디오 생성용 묘사 영어 프롬프트 (예: 'A photorealistic, tense close-up of a young North Korean girl's eyes...')")
    bg_color: str = "#1a1a2e"
    duration_sec: int = 3
    is_hook: bool = False

class VideoScript(BaseModel):
    title: str = Field(description="SEO 최적화 제목 (25~45자)")
    hook: str
    lang: str
    seo_description: str = Field(description="키워드 3회 반복 및 해시태그 포함")
    seo_tags: List[str] = Field(description="총 450자 이상의 태그 리스트")
    scenes: List[Scene]

def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: raise RuntimeError("GEMINI_API_KEY 누락")
    return genai.Client(api_key=api_key)

def _generate(client, prompt: str, response_schema=None, model_name: str = MODEL_PRO) -> str:
    try:
        config = {
            "temperature": 0.9,
            "max_output_tokens": 8192,
            "safety_settings": [types.SafetySetting(category=c, threshold=types.HarmBlockThreshold.BLOCK_NONE) for c in [types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, types.HarmCategory.HARM_CATEGORY_HARASSMENT, types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT]]
        }
        if response_schema: config["response_mime_type"], config["response_schema"] = "application/json", response_schema

        res = client.models.generate_content(model=model_name, contents=prompt, config=types.GenerateContentConfig(**config))
        return res.text.strip()
    except Exception as e:
        print(f"Gemini Error: {e}"); raise e

def recommend_topics(base_topic: str = None, channel_performance: dict = None) -> list[dict]:
    client = _get_client()
    if not base_topic or base_topic.strip() == "":
        base_topic = "가장 자극적이고 클릭률 높은 세계사 평행세계 미스테리"

    performance_context = ""
    if channel_performance:
        performance_context = f"(현재 채널 실적: 평균 SEO {channel_performance.get('avg_seo', 90)}점, 평균 예상 성과 {channel_performance.get('avg_views', 10000):,}회)"

    prompt = f"평행세계 다큐 PD로서 '{base_topic}' 주제의 자극적인 What If 소주제 5개를 기획하세요. {performance_context} 위 채널의 과거 실적을 고려하여, 각 주제별로 정밀 알고리즘 분석을 통한 예상 조회수를 산출하세요. 루프 물 유도 필수."
    raw = _generate(client, prompt, response_schema=TopicRecommendations, model_name=MODEL_FLASH)
    return json.loads(raw).get("topics", [])

def generate_script(topic_title: str, hook: str, style: str = "photorealistic", is_long_form: bool = False, lang: str = "ko", coupang_mode: bool = False) -> dict:
    client = _get_client()
    lang_name = LANGUAGES.get(lang, "한국어")

    # 모드에 따른 설정 변경
    num_scenes = 4
    if is_long_form: num_scenes = 24
    if coupang_mode: num_scenes = 30

    instruction = ""
    if coupang_mode:
        from .knowledge_engine import KnowledgeEngine
        viral_logic = KnowledgeEngine().get_strategy()
        instruction = f"\n[쿠팡 바이럴 모드 특수 지침]\n{viral_logic}\n- 20번 장면 근처에 역사적 위기를 해결할 '쿠팡 유물' 등장 및 링크 유도 멘트 포함.\n- 30번 장면 끝과 1번 장면 시작을 문법적으로 연결하여 무한 루프 구현."
    elif is_long_form:
        instruction = "\n- 24개 장면의 대서사시 다큐멘터리 형태로 구성할 것."
    else:
        instruction = "\n- 4개 장면의 핵심 요약 쇼츠 형태로 구성할 것."

    prompt = f"""
당신은 유튜브 알고리즘을 파괴하는 평행세계 다큐 작가입니다.
주제: "{topic_title}" (훅: {hook})
스타일: {style} / 언어: {lang_name}

[제작 지침]
1. 분량: 정확히 {num_scenes}개 장면 (씬당 3초 고정)
2. 27자의 법칙: 모든 'narration'과 'subtitle'은 반드시 공백 포함 **27자 이내**로 작성.
3. SEO 100점: vidIQ 100점 기준 (제목 키워드 전방 배치, 설명란 키워드 3회 반복, 태그 450자).
4. 검색용 키워드 분리:
   - 각 장면의 `image_query`는 위키미디어 Commons 등 실제 이미지 스톡 사이트에서 고증 사진을 검색하기 위한 **1~3단어 영어 핵심 명사 키워드 (예: 'Kim Ju-ae', 'Kim Jong-un', 'North Korea map', 'Pyongyang')** 여야 합니다. 절대 길고 복잡한 프롬프트를 적지 마세요.
   - 각 장면의 `video_query`는 스톡 비디오 검색을 위한 **1~3단어 영어 핵심 명사 키워드 (예: 'military parade', 'palace', 'korean border')** 여야 합니다.
   - 각 장면의 `ai_prompt`는 만약 1단계 고증 검색 실패 시, AI가 직접 그리기 위한 **구체적이고 극사실적인 고화질 영어 묘사 프롬프트 (예: 'A photorealistic close-up of a young North Korean girl...')** 를 작성하세요.
{instruction}

반드시 위 규칙을 지켜 JSON으로 반환하세요.
"""
    raw = _generate(client, prompt, response_schema=VideoScript, model_name=MODEL_PRO)
    return json.loads(raw)
