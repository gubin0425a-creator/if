import os
import sys
import time
import subprocess
import argparse
import re
import json

# Ensure stdout uses UTF-8
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

def run_single_generation(coupang_mode=False):
    print("\n[Worker] 🤖 AI 주제 추천 분석 가동...")
    try:
        from src.topic_recommender import recommend_topics
        topics = recommend_topics(base_topic="가상 역사 평행세계 미스터리", channel_performance={"avg_seo": 98, "avg_views": 50000})
        if not topics:
            print("[Worker] ❌ 주제 추천 실패: 빈 결과를 수신했습니다.")
            return False
            
        picked = topics[0]
        title = picked.get("title", "")
        hook = picked.get("hook", "")
        
        print(f"[Worker] ✅ 추천 선정 주제: '{title}' (훅: '{hook}')")
        
        # Build generator command
        cmd = [
            os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe"),
            "-u",
            os.path.join(BASE_DIR, "generate_video_v2.py"),
            "--topic", title,
            "--hook", hook,
            "--auto-upload"
        ]
        if coupang_mode:
            cmd.append("--coupang-mode")
            
        print(f"[Worker] 🚀 비디오 생성기 구동 시작: {' '.join(cmd)}")
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=BASE_DIR
        )
        
        while True:
            line = p.stdout.readline()
            if not line and p.poll() is not None:
                break
            if line:
                print(f"  [Gen] {line.strip()}")
                
        p.wait()
        if p.returncode == 0:
            print("[Worker] 🎉 비디오 생성 및 업로드 완료!")
            return True
        else:
            print(f"[Worker] ❌ 생성 프로세스 오류 종료 (Exit Code: {p.returncode})")
            return False
    except Exception as e:
        print(f"[Worker] ❌ 실행 중 치명적 오류 발생: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Chronos AI 자동화 팩토리/스케줄러 워커")
    parser.add_argument("--mode", type=str, required=True, choices=["factory", "24h"], help="작동 모드 (factory: 3개 즉시 제작, 24h: 24시간 주기 작동)")
    parser.add_argument("--coupang-mode", action="store_true", default=False, help="쿠팡 파트너스 모드 연동 여부")
    args = parser.parse_args()

    print("=" * 60)
    print(f"🏭 Chronos AI 자동 워커 가동 (모드: {args.mode}, 쿠팡모드: {args.coupang_mode})")
    print("=" * 60)

    if args.mode == "factory":
        print("\n[Factory] 🏭 30분 공장 모드 가동 (3회 연속 비디오 제작/업로드)")
        success_count = 0
        for i in range(3):
            print(f"\n──────────────────────────────────────────────────────────")
            print(f"⚙️ 공장 제 {i+1}호기 기동 시작")
            print(f"──────────────────────────────────────────────────────────")
            if run_single_generation(args.coupang_mode):
                success_count += 1
                print(f"  -> 제 {i+1}호기 완료 (누적 성공: {success_count}/3)")
            else:
                print(f"  -> 제 {i+1}호기 실패")
            # 씬 간 10초 대기
            time.sleep(10)
        print(f"\n[Factory] 🏁 공장 가동 종료! (최종 성공: {success_count}/3)")

    elif args.mode == "24h":
        print("\n[24h Engine] 🔄 24시간 무인 예약 자동화 엔진 시작 (6시간 주기로 상시 대기/가동)")
        loop_count = 0
        interval_seconds = 6 * 60 * 60 # 6시간 간격
        while True:
            loop_count += 1
            print(f"\n──────────────────────────────────────────────────────────")
            print(f"🔄 24h 무인 엔진 제 {loop_count}회차 루프 가동 ({time.strftime('%Y-%m-%d %H:%M:%S')})")
            print(f"──────────────────────────────────────────────────────────")
            run_single_generation(args.coupang_mode)
            
            print(f"\n[24h Engine] ⏱️ 다음 {interval_seconds // 3600}시간 뒤 루프를 위해 대기 상태로 진입합니다...")
            time.sleep(interval_seconds)

if __name__ == "__main__":
    main()
