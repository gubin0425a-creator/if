import os
import sys
import socket
import subprocess

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_master_code():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    code_path = os.path.join(base_dir, "..", "temp", "access_code.txt")
    if os.path.exists(code_path):
        with open(code_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def sync():
    print("="*60)
    print("📲 Chronos AI USB/ADB 원클릭 기기 동기화 유틸리티")
    print("="*60)

    # 1. PC IP 주소 감지
    pc_ip = get_local_ip()
    port = "5000"
    print(f"📡 감지된 PC 로컬 IP 주소: {pc_ip}:{port}")

    # 2. 마스터 코드 로드
    code = get_master_code()
    if not code:
        print("❌ 오류: 생성된 마스터 코드를 찾을 수 없습니다. app.py를 먼저 실행해 주세요.")
        sys.exit(1)
    print(f"🔐 로드된 마스터 코드 (일부): {code[:10]}...")

    # 3. ADB 연결 기기 확인
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=True)
        lines = res.stdout.strip().split("\n")[1:]
        devices = [line.split()[0] for line in lines if line.strip() and "device" in line]
    except Exception as e:
        print("❌ 오류: ADB 도구가 설치되어 있지 않거나 경로에 없습니다.")
        sys.exit(1)

    if not devices:
        print("⚠️ 경고: USB로 연결된 안드로이드 기기를 찾을 수 없습니다.")
        print("👉 스마트폰을 PC에 유선 연결하고 'USB 디버깅'이 활성화되어 있는지 확인해 주세요.")
        sys.exit(1)

    target_device = devices[0]
    print(f"📱 연결된 대상 안드로이드 기기 감지: {target_device}")

    # 4. ADB 인텐트 주입 명령 실행
    print("🚀 인텐트 주입 및 설정을 동기화하는 중...")
    cmd = [
        "adb", "-s", target_device, "shell", "am", "start",
        "-n", "com.example.chronosai/.MainActivity",
        "--es", "ip", pc_ip,
        "--es", "port", port,
        "--es", "master_code", code
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ 동기화 완료! 스마트폰 앱이 자동으로 다시 시작되어 PC 서버와 연결되었습니다.")
        print("🔗 이제 로그인 입력 없이 바로 스마트폰에서 대시보드로 진입 가능합니다.")
    except Exception as e:
        print(f"❌ 설정 주입 실패: {e}")

if __name__ == "__main__":
    sync()
