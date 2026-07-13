import os
import subprocess
import sys

def build():
    print("⚡ Chronos v4.0 Windows EXE 빌드를 시작합니다...")

    # 1. PyInstaller 설치 확인
    try:
        import PyInstaller
    except ImportError:
        print("[System] PyInstaller가 설치되어 있지 않습니다. 설치를 시작합니다...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. 빌드 명령어 구성
    # --onefile: 단일 파일로 생성
    # --noconsole: 실행 시 터미널 창 숨김 (로그를 보고 싶으면 제외)
    # --add-data: 에셋 및 소스 폴더 포함
    # --icon: 아이콘 파일이 있다면 경로 지정 가능

    cmd = [
        "pyinstaller",
        "--noconsole",
        "--name=Chronos_AI_Creator",
        "--add-data=src;src",
        "--add-data=assets;assets",
        "--add-data=NanumGothicBold.ttf;.",
        "--add-data=.env;.",
        "--collect-all=google.genai",
        "--collect-all=moviepy",
        "gui.py"
    ]

    print(f"[System] 실행 명령어: {' '.join(cmd)}")

    try:
        subprocess.check_call(cmd)
        print("\n" + "="*60)
        print("🎉 빌드 완료!")
        print("dist/ 폴더 안에서 Chronos_AI_Creator.exe 파일을 확인하세요.")
        print("="*60)
    except Exception as e:
        print(f"\n❌ 빌드 중 오류 발생: {e}")

if __name__ == "__main__":
    build()
