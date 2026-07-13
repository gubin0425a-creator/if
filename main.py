import os
import sys
import shutil
import json
import asyncio
from src.youtube_uploader import YouTubeUploader

import argparse

# Ensure output prints UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "videos_to_upload")
COMPLETED_DIR = os.path.join(BASE_DIR, "completed")
SRT_DIR = os.path.join(BASE_DIR, "subtitles")

for d in [INPUT_DIR, COMPLETED_DIR]:
    os.makedirs(d, exist_ok=True)

async def main():
    parser = argparse.ArgumentParser(description="틱톡 & 유튜브 통합 자동 업로더")
    parser.add_argument("--video", type=str, default=None, help="개별 업로드할 비디오 파일명 (예: auto_shorts_xxx.mp4)")
    args = parser.parse_args()

    print("=" * 60)
    print("🎬 유튜브 Shorts 전용 자동 업로드 파이프라인 (main.py)")
    print("=" * 60)

    if args.video:
        video_files = [args.video] if os.path.exists(os.path.join(INPUT_DIR, args.video)) else []
        if not video_files:
            print(f"\n[Main] 개별 지정된 동영상 파일을 찾을 수 없습니다: {args.video}")
            return
    else:
        video_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.mp4', '.mov'))]

    if not video_files:
        print(f"\n[Main] 업로드할 영상이 없습니다. 영상을 아래 폴더에 넣어주세요:")
        print(f"  -> {INPUT_DIR}")
        return

    print(f"\n[Main] 업로드 대기 중인 영상: {len(video_files)}개 발견")

    # Initialize YouTube Uploader
    youtube_uploader = YouTubeUploader()

    # Check YouTube Client Secrets
    has_youtube = os.path.exists(youtube_uploader.client_secrets_file)
    if not has_youtube:
        print("\n[Main] ⚠️ client_secrets.json이 없어 유튜브 업로드는 건너뜁니다.")
        print("         유튜브 업로드도 원하시면 구글 클라우드에서 클라이언트 키를 다운로드해")
        print("         프로젝트 폴더에 'client_secrets.json'으로 저장해 주세요.")

    for video_file in video_files:
        video_path = os.path.join(INPUT_DIR, video_file)
        print(f"\n──────────────────────────────────────────────────────────")
        print(f"📦 처리 대상 영상: {video_file}")
        print(f"──────────────────────────────────────────────────────────")

        # 1. Extract ascii_title to match metadata
        # Filename starts with auto_shorts_
        ascii_title = video_file
        if video_file.startswith("auto_shorts_"):
            ascii_title = video_file[len("auto_shorts_"):]
        if ascii_title.endswith(".mp4"):
            ascii_title = ascii_title[:-4]
        if ascii_title.endswith(".mov"):
            ascii_title = ascii_title[:-4]

        # Look for subtitles/{ascii_title}_metadata.json
        metadata_file = os.path.join(SRT_DIR, f"{ascii_title}_metadata.json")
        
        # Default fallback values
        title = ascii_title.replace("_", " ").strip()
        hook = "당신이 절대 몰랐던 평행세계 이야기"
        description = "흥미진진한 역사 다큐멘터리 쇼츠 영상입니다."
        tags = ["역사", "평행세계", "쇼츠", "다큐멘터리", "AlternativeHistory"]

        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    title = meta.get("title", title)
                    hook = meta.get("hook", hook)
                    description = meta.get("description", description)
                    tags = meta.get("tags", tags)
                print(f"[Main] ✅ 매칭되는 메타데이터 JSON 발견: {os.path.basename(metadata_file)}")
            except Exception as e:
                print(f"[Main] ⚠️ 메타데이터 로드 실패 (기본값 사용): {e}")
        else:
            print(f"[Main] ℹ️ 메타데이터 파일 없음. 기본값으로 태그를 지정합니다.")

        # 2. Build Captions/Titles
        # TikTok Caption
        tiktok_caption = f"🎬 {title}\n\n💬 {hook}\n\n" + " ".join([f"#{t}" for t in tags[:5]])
        # YouTube Title (max 100 chars)
        youtube_title = f"{title}"
        if len(youtube_title) > 85:
            youtube_title = youtube_title[:85]
        # YouTube Description
        youtube_description = f"{hook}\n\n{description}\n\n" + " ".join([f"#{t}" for t in tags])

        # ── B. 유튜브 업로드 실행 ──
        success_youtube = False
        if has_youtube:
            print("\n[Main] 🎥 유튜브 Shorts 자동 업로드 시작...")
            try:
                # Authenticate and upload
                youtube_uploader.authenticate()
                video_id = youtube_uploader.upload_shorts(
                    video_path=video_path,
                    title=youtube_title,
                    description=youtube_description,
                    tags=tags,
                    privacy_status="public" # public / private / unlisted
                )
                if video_id:
                    success_youtube = True
                    print(f"[Main] 유튜브 Shorts 업로드 성공! (ID: {video_id})")
                    # Save video ID to metadata
                    if os.path.exists(metadata_file):
                        try:
                            with open(metadata_file, "r", encoding="utf-8") as f:
                                meta = json.load(f)
                            meta['youtube_video_id'] = video_id
                            with open(metadata_file, "w", encoding="utf-8") as f:
                                json.dump(meta, f, ensure_ascii=False, indent=2)
                        except:
                            pass
            except Exception as e:
                print(f"[Main] ❌ 유튜브 업로드 중 오류 발생: {e}")
        else:
            print("\n[Main] ⚠️ client_secrets.json이 없어 업로드를 생략합니다.")

        # ── C. 작업 처리 결과 정리 ──
        if success_youtube:
            # Move uploaded video to completed directory
            completed_dest = os.path.join(COMPLETED_DIR, video_file)
            try:
                shutil.move(video_path, completed_dest)
                print(f"[Main] ✅ 원본 영상을 완료 폴더로 이동했습니다: {os.path.basename(completed_dest)}")
                # Also move metadata file if exists
                if os.path.exists(metadata_file):
                    shutil.move(metadata_file, os.path.join(COMPLETED_DIR, os.path.basename(metadata_file)))
            except Exception as e:
                print(f"[Main] 완료 폴더 이동 실패: {e}")
        else:
            print("[Main] ⚠️ 업로드 실패 또는 완료되지 않아 영상이 큐에 유지됩니다.")

    print("\n[Main] 모든 업로드 대기열 처리가 끝났습니다.")

if __name__ == "__main__":
    asyncio.run(main())
