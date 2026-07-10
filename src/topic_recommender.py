"""
topic_recommender.py
────────────────────
Gemini 2.5 Pro를 이용한 두 단계 생성 모듈:
  1) 기본 주제 → 5개 소주제 추천 (Structured Outputs 적용)
  2) 선택된 소주제 → 10장면 다큐 대본 (다국어 + 이미지 검색어 포함, Structured Outputs 적용)
     - 유튜브 공식 가이드 및 vidIQ 90점 이상 획득 룰을 적용한 SEO 최적화 메타데이터 자동 기획
     - 토큰 오버플로우 방지를 위한 콤팩트 다국어 지침 내장
"""
import os
import sys
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ── 환경변수 로드 ──────────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MODEL_NAME = "gemini-2.5-pro"   # 최고성능 Pro 모델로 업그레이드 (대본 품질 극대화)

LANGUAGES = {
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
}

# TTS 보이스 코드 (Edge-TTS)
TTS_VOICES = {
    "ko": "ko-KR-InJoonNeural",   # 남성 나레이터
    "en": "en-US-GuyNeural",
    "ja": "ja-JP-KeitaNeural",
}


# ── Pydantic Structured Output 스키마 정의 ─────────────────────────────────────
class TopicRecommendation(BaseModel):
    index: int = Field(description="주제의 인덱스 번호 (1~5)")
    title: str = Field(description="만약에(What If) ~했다면? 형태의 기발하고 자극적인 가상 역사 시나리오 제목")
    hook: str = Field(description="시청자의 3초 이탈을 방지할 자극적이고 흥미진진한 훅 질문")

class TopicRecommendations(BaseModel):
    topics: List[TopicRecommendation] = Field(description="추천하는 평행세계 가상 역사 소주제 5선 목록")

class Scene(BaseModel):
    scene_num: int = Field(description="장면 인덱스 번호 (1부터 10까지)")
    narration_ko: str = Field(description="한국어 나레이션 (하십시오체 다큐 성우 어조, 기승전결 역할에 맞는 구체적 수치/파급력 포함 정확히 2문장)")
    narration_en: str = Field(description="영어 나레이션 번역 (토큰 절약을 위해 정확히 1문장으로 극단적 콤팩트 서술)")
    narration_ja: str = Field(description="일본어 나레이션 번역 (토큰 절약을 위해 정확히 1문장으로 극단적 콤팩트 서술)")
    subtitle_ko: str = Field(description="한국어 자막 (핵심 팩트/결과를 정확히 전달하는 20~30자, 단순 질문 형태 금지)")
    subtitle_en: str = Field(description="영어 자막 번역 (토큰 절약을 위해 5~10단어 내외로 짧게)")
    subtitle_ja: str = Field(description="일본어 자막 번역 (토큰 절약을 위해 10~15자 내외로 짧게)")
    image_query: str = Field(description="Imagen 4 이미지 생성을 위한 구체적인 영어 씬 묘사 프롬프트 (비주얼 스타일 반영)")
    video_query: str = Field(description="B-roll 동영상 검색을 위한 영어 2~3단어 핵심 키워드")
    bg_color: str = Field(description="단색 폴백 배경색으로 사용할 RGB Hex 색상값 (예: #1a1a2e)")
    duration_sec: int = Field(description="장면의 지속 시간 (초 단위, 훅 장면인 1번 씬은 10초, 본문인 2~9번 씬은 12~14초, 마무리인 10번 씬은 10초)")
    is_hook: bool = Field(description="첫 번째 장면(시청자 훅 제시)인 경우 True, 그 외에는 False")

class VideoScript(BaseModel):
    title: str = Field(description="유튜브 최적화 SEO 타이틀 (20~45자 내외, 핵심 타겟 키워드 2개 이상을 반드시 제목 앞쪽 35% 영역에 배치, 호기심과 감정 자극)")
    hook: str = Field(description="비디오 전반을 아우르는 시청자 훅 질문")
    lang: str = Field(description="대본 기본 언어 코드 (ko)")
    seo_description: str = Field(description="유튜브 공식 가이드 최적화 설명란 본문. 반드시 첫 2줄(150자 이내)에 제목의 핵심 키워드를 2-3회 중복/반복 노출시켜야 하며, 본문 뒤쪽에 최소 3개에서 최대 5개의 해시태그(예: #Shorts, #무슨역사, #AlternativeHistory)를 필수 포함해야 함.")
    seo_tags: List[str] = Field(description="유튜브 검색 노출용 태그 배열 (최소 10개 이상, 총 글자수의 합이 400자 이상 500자 이하가 되도록 가치가 높은 핵심 연관 검색 키워드들을 상세히 추출, 제목/설명란 단어와 교집합되는 트리플 키워드 단어를 반드시 3개 이상 포함해야 함)")
    scenes: List[Scene] = Field(description="다큐멘터리를 조립하기 위한 정확히 10개의 장면 대본 목록")


def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 .env 파일에 없습니다.")
    return genai.Client(api_key=api_key)


def _generate(client, prompt: str, response_schema=None) -> str:
    """단순 텍스트 생성 헬퍼 - 역사/정치 갈등 민감도 차단을 막기 위해 세이프티 필터를 비활성화합니다."""
    try:
        config_args = {
            "temperature": 0.8,
            "max_output_tokens": 8192,
            "safety_settings": [
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]
        }
        if response_schema is not None:
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = response_schema
        else:
            config_args["response_mime_type"] = "application/json"

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(**config_args),
        )
        if not response or not response.text:
            raise RuntimeError("Gemini API의 응답이 비어있거나 세이프티 차단이 발생했습니다.")
        return response.text.strip()
    except Exception as e:
        print(f"  [Gemini API 오류]: {e}")
        raise e


def recommend_topics(base_topic: str) -> list[dict]:
    """
    기본 주제를 받아 5개의 구체적인 '가상 역사(What If)' 평행세계 소주제를 추천합니다.
    """
    client = _get_client()
    prompt = f"""
당신은 평행세계 및 가상역사(Alternative History) 다큐멘터리 전문 PD입니다.
사용자가 입력한 대주제를 바탕으로, "만약에 역사적 사실이 다르게 흘러갔다면 과거와 현재가 어떻게 변했을까?"라는 관점의 흥미진진한 틱톡/쇼츠용 평행세계 소주제 5개를 기획해 주세요.

기본 주제: "{base_topic}"

소주제 추천 규칙:
1. 모든 소주제는 반드시 **"만약에(What If) ~했다면?"**이라는 가상 시나리오 형태의 제목이어야 합니다.
2. 실제 과거의 역사적 사실과 현재의 우리 삶을 대조하여, 사건의 분기점에서 나타나는 **인과적 파급효과(예: 영토 손실, 문화의 상실, 거대한 경제 붕괴, 생존 위기 등)**를 깊고 흥미진진하게 상상하여 기획하세요.
3. 시청자의 호기심을 극대화할 수 있도록 미스터리하고 흥미 위주의 자극적인 타이틀과 3초 안에 이탈을 막는 훅(Hook)을 기획하세요.
"""
    raw = _generate(client, prompt, response_schema=TopicRecommendations)
    try:
        data = json.loads(raw)
        return data.get("topics", [])
    except Exception as e:
        print(f"  [recommend_topics] Structured Output 파싱 실패: {e}")
        print(f"  원문 응답:\n{raw}\n")
        raise RuntimeError("소주제 추천 응답을 JSON으로 변환하는 데 실패했습니다.")


def generate_script(topic_title: str, hook: str, style: str = "photorealistic") -> dict:
    """
    선택된 소주제로 10장면 다큐 대본을 생성합니다 (목표 영상 시간: 2분 30초~3분).
    각 장면에는 KO/EN/JA 나레이션, 자막, 이미지/영상 검색어가 포함됩니다.
    동시에 유튜브 공식 가이드와 vidIQ SEO 90점 이상 조건(트리플 키워드, 다중 키워드, 해시태그)을 강제 적용합니다.
    """
    client = _get_client()

    style_map = {
        "photorealistic": "ultra-photorealistic cinematic DSLR photography, National Geographic documentary style, 8K UHD, natural skin detail",
        "ink-painting": "traditional East Asian ink wash brush painting style, artistic historical illustration, soft brush strokes",
        "oil-painting": "classical historical oil painting style, textured canvas, dramatic chiaroscuro lighting",
        "webtoon": "modern anime webtoon style, vibrant colors, sharp cell shading, epic manhwa cover art"
    }
    style_desc = style_map.get(style, style_map["photorealistic"])

    prompt = f"""
당신은 가상 역사 및 평행세계(Alternative History & Parallel Universe) 전문 다큐멘터리 대본 작가입니다.
아래 가상 역사 주제로 유튜브 쇼츠/틱톡/인스타 릴스용 **2분 30초 ~ 3분** 분량의 흡입력 높고 깊은 다큐 대본을 **10개 씬**으로 작성하세요.

주제: "{topic_title}"
훅(Hook): "{hook}"
비주얼 이미지 연출 스타일: {style_desc}

## 유튜브 공식 SEO 알고리즘 및 vidIQ 90점 이상 획득 규칙 (필수 준수)
당신이 생성할 메타데이터(`title`, `seo_description`, `seo_tags`)는 자체 SEO 채점기에서 반드시 90점 이상을 획득해야 합니다. 다음 규격을 극한으로 준수하여 작곡하세요.

1. **태그 개수 및 볼륨 (Tag Count & Volume)**:
   - `seo_tags` 배열은 반드시 최소 10개 이상의 검색 키워드를 포함해야 합니다.
   - 각 태그의 총 글자수 합(구분자 포함)이 최소 400자 이상(유튜브 한계 500자 근접)이 되도록 핵심 연관 키워드를 풍부하게 서술하세요. (예: "임진왜란 평행세계", "임진왜란 만약에", "조선 역사 다큐", "역사 shorts", "대체역사 다큐멘터리" 등 구체적이고 길게 여러 개를 만드세요.)
2. **제목 내 키워드 배치 (Keywords in Title)**:
   - `title`은 20자 이상 45자 이내로 작성하세요.
   - 핵심 타겟 키워드 2개(예: 임진왜란, 조선 등)를 **제목 시작 35% 이내 앞부분 영역**에 무조건 배치하세요. 호기심을 극한으로 자극하는 문구로 작성하세요.
3. **설명란 키워드 반복 (Keywords in Description)**:
   - `seo_description` 설명란의 첫 150글자(첫 2줄) 영역에 제목의 핵심 키워드를 자연스러운 문맥으로 2~3회 반복 배치하여 매칭률을 극대화하세요.
4. **트리플 키워드 매칭 (Tripled Keywords)**:
   - `title`, `seo_description`, `seo_tags` 세 영역 모두에 공통으로 중복 포함되는 핵심 명사 단어(트리플 키워드)를 최소 3개 이상 완벽히 매칭되도록 동기화하여 작성하세요.
5. **해시태그 최적화 (Hashtags)**:
   - `seo_description` 최하단에 `#Shorts`를 필수로 포함하여, `#Shorts #AlternativeHistory #역사다큐` 등 총 3개에서 5개 사이의 명확한 해시태그를 포함하세요. (6개 초과 금지)

## 핵심 요구사항 (매우 중요 - 반드시 준수하세요)

### 토큰 세이브를 위한 다국어 요약 지침
- 출력 응답 제한으로 인한 잘림 에러를 방지하기 위해 **영문(en) 및 일문(ja) 필드는 반드시 1문장의 아주 단순하고 콤팩트한 요약문**으로만 채우세요. 절대 길게 쓰지 마십시오.
- 한국어 나레이션도 장황한 부가 설명을 자제하고 **핵심적 역사 파급력 위주의 콤팩트한 2문장**으로 확실하게 전달하세요.

### 내용 구조: "가정 → 근거 → 결과" 3단계 서술
모든 씬은 "만약에 ~했다면?"이라는 가정에서 시작해 실제 역사적 근거와 구체적인 현재의 결과까지 긴밀히 연결되어야 합니다.
반드시 아래 3단계 구조를 모든 씬에 적용하세요:
1. **가정 제시**: "만약 ~했다면" (1문장)
2. **역사적 근거**: "실제 역사에서는 ~였기 때문에" (1~2문장)  
3. **구체적 결과/파급효과**: "그 결과 ~가 되었을 것입니다" (2~3문장)

### 씬별 역할 배분 (기승전결)
- **씬 1 [훅]**: 시청자를 단숨에 낚는 충격적인 결과를 먼저 제시. "~가 사라졌습니다" 형태로 결과부터 보여준다.
- **씬 2~3 [역사적 배경]**: 실제 역사적 사실과 분기점을 구체적 연도/인물/사건과 함께 설명. "실제로 {{연도}}년에 ~가 일어났습니다" 형태.
- **씬 4~5 [분기 직후]**: 역사가 다르게 흘러간 직후 1~10년 내의 즉각적인 변화를 구체적 수치와 함께 서술. 인구 변동, 영토 변화, 권력 이동 등.
- **씬 6~7 [연쇄 파급]**: 그 변화가 50~100년에 걸쳐 일으킨 연쇄 반응. 문화, 언어, 경제, 기술 발전에 미친 영향을 구체적으로.
- **씬 8~9 [현재에 미친 영향]**: 그 평행세계가 지금 2020년대의 우리 삶에 어떤 차이를 만들었을지. K-POP, 한류, IT산업, 일상 문화 등 시청자가 공감할 수 있는 현재의 사례와 대조.
- **씬 10 [마무리]**: 현실 역사의 소중함을 되새기며, "우리가 당연하게 누리는 ~는 사실 기적적인 결과물입니다"라는 메시지. 구독/팔로우 CTA.

### 나레이션 분량 (핵심)
- 나레이션은 3개 언어(한국어, 영어, 일본어)로 작성하세요.
- **씬 1(훅): 2문장** (약 8~10초 분량)
- **씬 2~9(본문): 2~3문장** (약 10~12초 분량) — 팩트 위주로 콤팩트하면서도 핵심 정보만 담으세요.
- **씬 10(마무리): 2문장** (약 8~10초 분량)
- 어조: 평행세계 다큐멘터리 성우처럼 **경고하는 듯하면서도 중후하고 차분하며 격식 있는 어조** (한국어: 하십시오체). 번역은 자연스러운 원어민 표현으로.
- **모든 문장은 구체적 사실, 수치, 결과를 포함**해야 합니다. 막연한 질문이나 추상적 서술은 금지합니다.

### 자막
- 자막은 나레이션의 핵심 결과/팩트를 **정확하게 전달하는 20~30자** (한국어)로 작성하세요.
- 단순 질문이 아닌, 시청자가 읽었을 때 "와, 진짜?" 하고 반응할 구체적 결과를 담으세요.
- 영문 자막: 5~10단어 내외, 일본어 자막: 10~15자 내외로 매우 짧게.
"""
    raw = _generate(client, prompt, response_schema=VideoScript)
    try:
        return json.loads(raw)
    except Exception as e:
        print(f"  [generate_script] Structured Output 파싱 실패: {e}")
        # cp949 인코딩 에러 방지 처리하여 안전하게 로그 기록
        try:
            safe_raw = raw.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
            print(f"  원문 응답:\n{safe_raw}\n")
        except Exception as print_err:
            print(f"  [로그 출력 실패]: {print_err}")
        raise RuntimeError("다큐 대본 응답을 JSON으로 변환하는 데 실패했습니다.")
