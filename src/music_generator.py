"""
src/music_generator.py
───────────────────────
AI 배경음악 자동 생성 모듈
  1) Freesound API  – 분위기별 CC 라이선스 음악 자동 검색 + 다운로드 (무료)
  2) Mubert API     – 키 등록 시 AI 생성 음악 사용 (선택)
"""
import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY", "")
MUBERT_API_KEY    = os.getenv("MUBERT_API_KEY", "")

HEADERS = {"User-Agent": "TikTokAutoBot/2.0"}

# ── 분위기 → 검색어 매핑 ─────────────────────────────────────────────────────
MOOD_QUERIES = {
    "epic":     ["epic orchestral battle", "cinematic war drums", "historical epic music"],
    "mystery":  ["mysterious ancient documentary", "dark ambient history", "suspense orchestral"],
    "sad":      ["sad piano history", "mournful orchestral", "emotional documentary"],
    "tension":  ["tense thriller orchestral", "dramatic suspense", "battle tension music"],
    "neutral":  ["documentary background music", "cinematic ambient history", "ancient civilization"],
}

MOOD_TAGS_MUBERT = {
    "epic":    ["epic", "orchestral", "cinematic", "action"],
    "mystery": ["mysterious", "ambient", "dark", "cinematic"],
    "sad":     ["sad", "emotional", "piano", "orchestral"],
    "tension": ["tense", "thriller", "dramatic", "orchestral"],
    "neutral": ["documentary", "ambient", "cinematic", "calm"],
}


def _detect_mood(script_data: dict) -> str:
    """대본 데이터를 분석하여 분위기를 자동 감지합니다."""
    title = script_data.get("title", "").lower()
    all_text = " ".join([
        s.get("narration_ko", "") for s in script_data.get("scenes", [])
    ]).lower()

    if any(w in title + all_text for w in ["패배", "망", "죽음", "슬픔", "멸망", "비극"]):
        return "sad"
    if any(w in title + all_text for w in ["전투", "전쟁", "군사", "승리", "영웅", "영웅적"]):
        return "epic"
    if any(w in title + all_text for w in ["숨겨진", "비밀", "진실", "음모", "의문"]):
        return "mystery"
    if any(w in title + all_text for w in ["공포", "위기", "위험", "긴장", "절박"]):
        return "tension"
    return "neutral"


# ─────────────────────────────────────────────────────────────────────────────
# Freesound API
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_freesound(query: str, min_duration: int = 30, save_path: str = "") -> bool:
    """Freesound에서 CC 라이선스 음악을 검색하고 다운로드합니다."""
    if not FREESOUND_API_KEY or "your_" in FREESOUND_API_KEY:
        return False
    try:
        url = "https://freesound.org/apiv2/search/text/"
        params = {
            "query": query,
            "token": FREESOUND_API_KEY,
            "fields": "id,name,duration,license,previews",
            "filter": f"duration:[{min_duration} TO 300]",
            "sort": "rating_desc",
            "page_size": 5,
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        results = data.get("results", [])

        for r in results:
            license_url = r.get("license", "")
            # CC0 또는 CC BY 라이선스만 허용
            if "licenses/by/" not in license_url and "publicdomain/zero" not in license_url:
                continue
            # HQ 미리보기 MP3 다운로드
            preview_url = r.get("previews", {}).get("preview-hq-mp3", "")
            if not preview_url:
                continue
            audio_resp = requests.get(
                preview_url,
                headers={**HEADERS, "Authorization": f"Token {FREESOUND_API_KEY}"},
                timeout=30
            )
            if audio_resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(audio_resp.content)
                print(f"  [Music] ✅ Freesound 음악 저장: '{r['name']}' ({r['duration']:.0f}s)")
                return True

        print(f"  [Music] Freesound '{query}' 결과 없음 또는 라이선스 제한")
        return False
    except Exception as e:
        print(f"  [Music] Freesound 오류: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Mubert API (선택)
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_mubert(mood: str, duration: int, save_path: str) -> bool:
    """Mubert API로 AI 생성 음악을 다운로드합니다."""
    if not MUBERT_API_KEY or "your_" in MUBERT_API_KEY:
        return False
    try:
        tags = MOOD_TAGS_MUBERT.get(mood, MOOD_TAGS_MUBERT["neutral"])
        url = "https://api-b2b.mubert.com/v2/RecordTrackTTM"
        payload = {
            "method": "RecordTrackTTM",
            "params": {
                "pat": MUBERT_API_KEY,
                "duration": duration,
                "tags": tags,
                "format": "mp3",
                "intensity": "medium",
            }
        }
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        track_url = data.get("data", {}).get("tasks", [{}])[0].get("download_link", "")
        if not track_url:
            return False
        # 폴링: 트랙 생성에 시간이 걸릴 수 있음
        for _ in range(10):
            time.sleep(3)
            tr = requests.get(track_url, timeout=10)
            if tr.status_code == 200 and len(tr.content) > 1000:
                with open(save_path, "wb") as f:
                    f.write(tr.content)
                print(f"  [Music] ✅ Mubert AI 음악 저장 (분위기: {mood})")
                return True
        return False
    except Exception as e:
        print(f"  [Music] Mubert 오류: {e}")
        return False


def _generate_local_audiocraft(mood: str, duration: int, save_path: str) -> bool:
    """로컬에 설치된 Meta AudioCraft (MusicGen) 모델을 사용하여 고품질 배경음악을 직접 작곡합니다."""
    try:
        import torch
        # CUDA(NVIDIA GPU) 가속 확인
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"  [Music] 🚀 Meta AudioCraft 로컬 음악 생성 시도 (가속 장치: {device.upper()})...")
        
        # torch 경고 무시
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        
        from audiocraft.models import MusicGen
        from audiocraft.data.audio import audio_write
        
        # 모델 로드 (가벼운 musicgen-small 사용 - 용량 1.2GB로 고품질 멜로디 생성 가능)
        print("  [Music] AI 작곡 모델 로드 중 (musicgen-small)...")
        print("  [Music] 💡 최초 실행 시 HuggingFace에서 가중치(1.2GB)를 자동으로 다운로드하므로 시간이 조금 걸릴 수 있습니다.")
        model = MusicGen.get_pretrained('facebook/musicgen-small', device=device)
        
        # 분위기별 맞춤형 AI 작곡 프롬프트 생성
        prompt_map = {
            "epic": "Epic historical cinematic orchestral track, powerful war drums, brass ensemble, hero journey mood, studio recording, high quality",
            "mystery": "Dark mysterious ambient background music for historical documentary, slow tension, subtle soundscapes, high quality",
            "sad": "Emotional sad piano and string orchestra, mournful melody, historical tragedy documentary mood, cinematic, high quality",
            "tension": "Tense cinematic suspense background, rapid violin staccatos, rising panic, thriller scene mood, studio sound",
            "neutral": "Cinematic ambient orchestral background music, ancient history documentary theme, calm and grand, high quality"
        }
        prompt = prompt_map.get(mood, prompt_map["neutral"])
        
        model.set_generation_params(duration=duration)
        print(f"  [Music] AI 음악 작곡 중: '{prompt}' (재생 시간: {duration}초)...")
        
        # 작곡 실행
        wav = model.generate([prompt])
        
        # 오디오 파일로 저장
        temp_base = save_path.rsplit(".", 1)[0]
        audio_write(temp_base, wav[0].cpu(), model.sample_rate, strategy="loudness", loudness_compressor=True)
        
        wav_path = temp_base + ".wav"
        if os.path.exists(wav_path):
            if wav_path != save_path:
                if os.path.exists(save_path):
                    os.remove(save_path)
                os.rename(wav_path, save_path)
            print(f"  [Music] ✅ 로컬 AI 배경음악 작곡 완료: {os.path.basename(save_path)}")
            return True
        return False
    except Exception as e:
        print(f"  [Music] ⚠️  로컬 AI 음악 생성 실패 ({e}). 웹 API 검색 폴백을 진행합니다...")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 통합 음악 생성기 (공개 인터페이스)
# ─────────────────────────────────────────────────────────────────────────────
def generate_background_music(
    script_data: dict,
    output_path: str,
    mood: str = "auto",
    target_duration: int = 60,
) -> str | None:
    """
    대본 데이터를 기반으로 분위기에 맞는 배경음악을 자동 생성/검색합니다.
    반환: 저장된 음악 파일 경로 (없으면 None)
    """
    # 분위기 자동 감지
    if mood == "auto":
        mood = _detect_mood(script_data)
 
    print(f"  [Music] 🎵 분위기 감지: '{mood}' → 배경음악 생성/검색 시작...")
 
    # ── 1순위: Meta AudioCraft 로컬 AI 작곡 (GPU/CPU 가속) ────────────────────────
    if _generate_local_audiocraft(mood, target_duration, output_path):
        return output_path
 
    # ── 2순위: Mubert AI API 생성 (폴백) ────────────────────────────────────────
    if _fetch_mubert(mood, target_duration, output_path):
        return output_path
 
    # ── 3순위: Freesound API 검색 (폴백) ────────────────────────────────────────
    queries = MOOD_QUERIES.get(mood, MOOD_QUERIES["neutral"])
    for query in queries:
        if _fetch_freesound(query, min_duration=30, save_path=output_path):
            return output_path
 
    # ── 4순위: assets/music/ 폴더의 기존 파일 사용 (폴백) ───────────────────────
    music_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'music')
    local_files = [
        os.path.join(music_dir, f)
        for f in os.listdir(music_dir)
        if f.lower().endswith((".mp3", ".wav", ".m4a"))
    ] if os.path.exists(music_dir) else []
 
    if local_files:
        import random
        selected_track = random.choice(local_files)
        print(f"  [Music] 로컬 음악 무작위 선택 사용: {os.path.basename(selected_track)}")
        return selected_track
 
    print(f"  [Music] ⚠️  배경음악 없음 (Freesound API 키를 등록하면 자동 검색됩니다)")
    return None
