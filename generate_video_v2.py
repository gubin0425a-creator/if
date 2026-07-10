"""
generate_video_v2.py
────────────────────
다큐멘터리 AI 숏폼 자동 제작 파이프라인 v2.0 메인 실행 스크립트

실행 흐름:
  1) 사용자 기본 주제 입력
  2) Gemini 3.5 Flash → 5개 소주제 추천 → 사용자 선택
  3) Gemini 3.5 Flash → 5개 씬 대본 생성 (KO/EN/JA 다국어)
  4) Wikimedia / Pixabay / Pexels → 장면별 역사 미디어 수집
  5) Edge-TTS → 한국어 나레이션 음성 생성
  6) 자막(KO/EN/JA) 합성 + SRT 파일 저장
  7) MoviePy → 장면 조립 + 배경음악 믹싱
  8) 최종 MP4 → videos_to_upload/ 저장

사용법:
  .venv\\Scripts\\python generate_video_v2.py
  .venv\\Scripts\\python generate_video_v2.py --topic "임진왜란"
  .venv\\Scripts\\python generate_video_v2.py --topic "임진왜란" --lang en
"""
import os
import sys
import time
import asyncio
import argparse
import shutil
from typing import Optional

# Windows 터미널 UTF-8 출력 강제
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

import edge_tts
import numpy as np
from PIL import Image

from src.topic_recommender import recommend_topics, generate_script, TTS_VOICES
from src.media_fetcher      import fetch_scene_media
from src.subtitle_renderer  import draw_subtitle_on_image, save_srt_files
from src.video_assembler    import build_scene_clip, assemble_final_video

# ── 디렉토리 설정 ──────────────────────────────────────────────────────────────
TEMP_DIR      = os.path.join(BASE_DIR, "temp")
UPLOAD_DIR    = os.path.join(BASE_DIR, "videos_to_upload")
SRT_DIR       = os.path.join(BASE_DIR, "subtitles")
MUSIC_DIR     = os.path.join(BASE_DIR, "assets", "music")
FONT_PATH     = os.path.join(BASE_DIR, "NanumGothicBold.ttf")

for d in [TEMP_DIR, UPLOAD_DIR, SRT_DIR, MUSIC_DIR]:
    os.makedirs(d, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: 주제 추천 인터랙티브 메뉴
# ─────────────────────────────────────────────────────────────────────────────
def select_topic(base_topic: Optional[str] = None, auto_pick: Optional[int] = None) -> tuple[str, str]:
    """
    기본 주제를 받아 5개의 소주제를 추천하고 사용자가 선택하도록 합니다.
    auto_pick이 지정되면 해당 번호를 자동 선택합니다.
    반환: (선택된 title, hook)
    """
    if not base_topic:
        base_topic = input("\n📌 기본 주제를 입력하세요 (예: 조선시대, 임진왜란, 세종대왕): ").strip()

    print(f"\n⏳ Gemini AI가 '{base_topic}'에 대한 소주제를 추천하고 있습니다...\n")
    topics = recommend_topics(base_topic)

    print("━" * 56)
    print("  📺 Gemini AI 추천 숏폼 소주제 5선")
    print("━" * 56)
    for t in topics:
        print(f"  [{t['index']}] {t['title']}")
        print(f"      💬 훅: {t['hook']}")
        print()
    print("━" * 56)

    # 자동 선택 모드
    if auto_pick is not None:
        selected = next((t for t in topics if t["index"] == auto_pick), None)
        if selected:
            print(f"\n✅ 자동 선택됨 [{auto_pick}]: '{selected['title']}'")
            return selected["title"], selected["hook"]

    while True:
        choice = input("선택 (1~5, 또는 0 = 직접 입력): ").strip()
        if choice == "0":
            custom_title = input("소주제 직접 입력: ").strip()
            custom_hook  = input("훅(Hook) 질문 직접 입력: ").strip()
            return custom_title, custom_hook
        try:
            idx = int(choice)
            selected = next((t for t in topics if t["index"] == idx), None)
            if selected:
                print(f"\n✅ 선택됨: '{selected['title']}'")
                return selected["title"], selected["hook"]
        except ValueError:
            pass
        print("⚠️  올바른 번호를 입력해주세요 (1~5 또는 0)")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: TTS 음성 생성 (Edge-TTS, 비동기)
# ─────────────────────────────────────────────────────────────────────────────
async def _generate_tts(text: str, voice: str, output_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


async def generate_all_audio(scenes: list[dict], lang: str = "ko") -> list[str]:
    """모든 장면의 나레이션 오디오 파일을 병렬로 생성합니다."""
    voice = TTS_VOICES.get(lang, TTS_VOICES["ko"])
    tasks = []
    paths = []
    for i, scene in enumerate(scenes):
        narration_key = f"narration_{lang}"
        text = scene.get(narration_key, scene.get("narration_ko", ""))
        out  = os.path.join(TEMP_DIR, f"audio_scene_{i}.mp3")
        paths.append(out)
        tasks.append(_generate_tts(text, voice, out))

    print(f"  [TTS] 🎧 {len(tasks)}개 장면 음성 생성 중... (언어: {lang})")
    await asyncio.gather(*tasks)
    print(f"  [TTS] ✅ 음성 생성 완료")
    return paths


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: 역사 미디어 수집
# ─────────────────────────────────────────────────────────────────────────────
def collect_media(scenes: list[dict], media_type: str = "image", aspect_ratio: str = "9:16") -> list[dict]:
    """각 장면에 맞는 영상/이미지를 수집합니다."""
    media_list = []
    print(f"  [Media] 🔍 {len(scenes)}개 장면 미디어 수집 중...")
    for i, scene in enumerate(scenes):
        print(f"    장면 {i+1}: '{scene.get('image_query', '')}' / '{scene.get('video_query', '')}'")
        media = fetch_scene_media(scene, i, TEMP_DIR, media_type, aspect_ratio)
        media_list.append(media)
    return media_list


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: 배경음악 선택
# ─────────────────────────────────────────────────────────────────────────────
def pick_background_music() -> Optional[str]:
    """assets/music/ 에서 배경음악 파일을 자동 선택합니다."""
    music_files = [
        os.path.join(MUSIC_DIR, f)
        for f in os.listdir(MUSIC_DIR)
        if f.lower().endswith((".mp3", ".wav", ".m4a"))
    ]
    if music_files:
        picked = music_files[0]
        print(f"  [Music] 🎵 배경음악: {os.path.basename(picked)}")
        return picked
    print("  [Music] ℹ️  assets/music/ 폴더에 음악 파일이 없습니다. (무음 처리)")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: 장면 클립 생성
# ─────────────────────────────────────────────────────────────────────────────
def build_all_clips(
    scenes: list[dict],
    media_list: list[dict],
    audio_paths: list[str],
    subtitle_lang: str = "ko",
    aspect_ratio: str = "9:16",
) -> list:
    """모든 장면의 MoviePy VideoClip을 생성합니다."""
    clips = []
    print(f"  [Build] 🎬 장면 클립 조립 중...")
    for i, (scene, media, audio) in enumerate(zip(scenes, media_list, audio_paths)):
        print(f"    장면 {i+1}/{len(scenes)}: {scene.get(f'subtitle_{subtitle_lang}', '')}")
        clip = build_scene_clip(scene, media, audio, FONT_PATH, subtitle_lang, aspect_ratio)
        clips.append(clip)
    return clips


# ─────────────────────────────────────────────────────────────────────────────
# 메인 파이프라인
# ─────────────────────────────────────────────────────────────────────────────
async def run_pipeline(
    base_topic: Optional[str] = None, 
    subtitle_lang: str = "ko", 
    auto_pick: Optional[int] = None,
    style: str = "photorealistic",
    mood: str = "auto",
    hook: Optional[str] = None,
    media_type: str = "image",
    aspect_ratio: str = "9:16"
):
    print()
    print("=" * 60)
    print("  🎬  AI 다큐 숏폼 자동 제작기 v3.5")
    print("  모델: Gemini 2.5 Pro (대본) + Gemini 3.1 Flash Image (미디어)")
    print("  자막: KO/EN/JA 다국어   |  음성: Edge-TTS  |  음악: AudioCraft AI")
    print("=" * 60)

    # ── 1. 주제 선택 ──────────────────────────────────────────────────────────
    # UI에서 구체적인 소주제와 훅이 직접 넘어온 경우 추천 단계를 건너뜁니다.
    if base_topic and hook:
        title = base_topic
        print(f"\n✅ 지정된 카드 주제와 훅으로 즉시 제작을 시작합니다:")
        print(f"   주제: '{title}'")
        print(f"   훅: '{hook}'")
    else:
        title, hook = select_topic(base_topic, auto_pick=auto_pick)

    # ── 2. 대본 생성 ──────────────────────────────────────────────────────────
    print(f"\n⏳ Gemini AI가 '{title}' 대본({style} 스타일)을 작성하고 있습니다...")
    script_data = generate_script(title, hook, style=style)
    scenes = script_data.get("scenes", [])
    print(f"✅ 대본 완성! {len(scenes)}개 장면")
    
    # [Feature] 나오는 나레이션을 모두 자막으로 연동 (subtitle을 narration으로 통대입)
    for s in scenes:
        for l in ["ko", "en", "ja"]:
            narr_text = s.get(f"narration_{l}", "")
            if narr_text:
                # 자막의 어색한 요약본 대신 나레이션 전체 대사가 자막으로 굽혀지도록 변경
                s[f"subtitle_{l}"] = narr_text

    for i, s in enumerate(scenes):
        print(f"   씬 {i+1}: {s.get('subtitle_ko', '')}")

    # ── 3. SRT 자막 파일 저장 ─────────────────────────────────────────────────
    print(f"\n📝 다국어 자막(.srt) 생성 중...")
    # Windows 한글 경로 오류를 막기 위해 파일명은 영문/숫자로만 제한
    import re
    ascii_title = re.sub(r'[^a-zA-Z0-9_\-]', '', title[:30]).strip()
    if not ascii_title:
        ascii_title = f"video_{int(time.time())}"
    save_srt_files(scenes, SRT_DIR, ascii_title)
    
    # Save video metadata JSON for automatic title/description upload with SEO scoring
    import json
    from src.seo_analyzer import SEOAnalyzer

    # Use AI-optimized SEO metadata from script_data
    seo_title = script_data.get("title", title)
    seo_desc = script_data.get("seo_description", "")
    if not seo_desc:
        seo_desc = "\n".join([s.get(f"narration_{subtitle_lang}", s.get("narration_ko", "")) for s in scenes])
        
    seo_tags = script_data.get("seo_tags", [])
    if not seo_tags:
        seo_tags = ["역사", "평행세계", "쇼츠", "다큐멘터리", "AlternativeHistory", "WhatIf"]

    # Calculate real-time SEO score based on vidIQ logic
    seo_res = SEOAnalyzer.calculate_seo_score(seo_title, seo_desc, seo_tags)
    
    metadata = {
        "title": seo_title,
        "hook": hook,
        "description": seo_desc,
        "tags": seo_tags,
        "seo_score": seo_res.get("seo_score", 0),
        "seo_report": seo_res.get("seo_report", {}),
        "triple_keywords": seo_res.get("triple_keywords_list", [])
    }
    
    metadata_path = os.path.join(SRT_DIR, f"{ascii_title}_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"  [Metadata] ✅ SEO 최적화 메타데이터 JSON 저장 완료 (SEO 점수: {seo_res.get('seo_score')}점): {os.path.basename(metadata_path)}")

    # ── 4. 역사 미디어 수집 ───────────────────────────────────────────────────
    print(f"\n🔍 역사 영상/이미지 수집 중...")
    media_list = collect_media(scenes, media_type, aspect_ratio)

    # ── 5. TTS 음성 생성 ──────────────────────────────────────────────────────
    print(f"\n🎧 나레이션 음성 생성 중 (언어: {subtitle_lang})...")
    audio_paths = await generate_all_audio(scenes, subtitle_lang)

    # ── 6. 배경음악 자동 생성 및 검색 ───────────────────────────────────────────
    bg_music_path = os.path.join(TEMP_DIR, "ai_background_music.mp3")
    from src.music_generator import generate_background_music
    bg_music = generate_background_music(script_data, bg_music_path, mood=mood, target_duration=60)

    # ── 7. 장면 클립 조립 ─────────────────────────────────────────────────────
    print(f"\n🎬 장면별 영상 클립 조립 중...")
    clips = build_all_clips(scenes, media_list, audio_paths, subtitle_lang, aspect_ratio)

    # ── 8. 최종 영상 렌더링 ───────────────────────────────────────────────────
    output_filename = f"auto_shorts_{ascii_title}.mp4"
    output_path = os.path.join(UPLOAD_DIR, output_filename)
    print(f"\n🎥 최종 영상 렌더링 중...")
    assemble_final_video(clips, output_path, bg_music, music_volume=0.15)

    # ── 9. 임시 파일 정리 ─────────────────────────────────────────────────────
    print(f"\n🧹 임시 파일 정리 중...")
    for media in media_list:
        if media.get("path") and os.path.exists(media["path"]):
            try: os.remove(media["path"])
            except: pass
    for ap in audio_paths:
        if os.path.exists(ap):
            try: os.remove(ap)
            except: pass
    if bg_music and bg_music == bg_music_path and os.path.exists(bg_music_path):
        try: os.remove(bg_music_path)
        except: pass

    # ── 완료 ──────────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  🎉 영상 제작 완료!")
    print(f"  📂 영상: {output_path}")
    print(f"  📝 자막: {SRT_DIR}\\")
    print()
    print("  다음 단계:")
    print("  → .venv\\Scripts\\python main.py  (틱톡 자동 업로드)")
    print("=" * 60)

    # 사용된 클립 리소스 해제
    for clip in clips:
        try: clip.close()
        except: pass


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 다큐 숏폼 자동 제작기 v2.0")
    parser.add_argument("--topic", type=str, default=None,
                        help="기본 주제 (예: '임진왜란', '세종대왕'). 생략 시 대화형 입력.")
    parser.add_argument("--lang", type=str, default="ko",
                        choices=["ko", "en", "ja"],
                        help="나레이션 및 자막 언어 (기본: ko)")
    parser.add_argument("--pick", type=int, default=None,
                         help="추천 주제 번호 자동 선택 (1~5). 지정 시 대화형 입력 없이 바로 진행.")
    parser.add_argument("--style", type=str, default="photorealistic",
                         choices=["photorealistic", "ink-painting", "oil-painting", "webtoon"],
                         help="AI 이미지 생성 비주얼 스타일 (기본: photorealistic)")
    parser.add_argument("--mood", type=str, default="auto",
                         choices=["auto", "epic", "mystery", "sad", "tension", "neutral"],
                         help="배경음악 분위기 스타일 (기본: auto)")
    parser.add_argument("--hook", type=str, default=None,
                         help="추천 소주제의 훅(Hook) 질문. 지정 시 추천 단계를 바이패스합니다.")
    parser.add_argument("--media-type", type=str, default="image",
                         choices=["image", "video"],
                         help="비주얼 미디어 타입 (기본: image)")
    parser.add_argument("--aspect-ratio", type=str, default="9:16",
                         choices=["9:16", "16:9"],
                         help="비디오 화면 비율 (기본: 9:16)")
    args = parser.parse_args()
 
    asyncio.run(run_pipeline(args.topic, args.lang, args.pick, args.style, args.mood, args.hook, args.media_type, args.aspect_ratio))
