"""
build_apk.py -- Chronos Mobile APK Wrapper Generator
이 스크립트는 PC 서버의 Flask 주소를 모바일 앱(APK)으로 변환하기 위한 설정 가이드를 생성합니다.
안드로이드 기기에서 실제 설치 가능한 전용 앱으로 구동됩니다.
"""
import os

def generate_build_config(server_url="http://[YOUR_PC_IP]:5000/mobile"):
    print("\n" + "="*70)
    print("📱 Chronos Mobile v4.5 전용 APK 빌드 가이드")
    print("="*70)
    print(f"\n1. 빌드 대상 주소: {server_url}")
    print("\n2. 빌드 환경 요구사항:")
    print("   - Buildozer (Linux/Colab 추천)")
    print("   - Kivy / KivyMD (Python Mobile Framework)")

    config_content = f"""
[app]
title = Chronos AI
package.name = chronos.ai.creator
package.domain = org.chronos
source.dir = .
version = 4.5
requirements = python3,kivy,requests,certifi
orientation = portrait
fullscreen = 1
android.permissions = INTERNET

# 메인 서버 연동 URL (PC의 내부 IP를 입력해야 합니다)
# buildozer.spec 파일에서 아래 주소를 수정하여 빌드하세요.
server_url = {server_url}
"""

    with open("mobile_build.spec", "w", encoding="utf-8") as f:
        f.write(config_content)

    print("\n✅ 'mobile_build.spec' 파일이 생성되었습니다.")
    print("👉 이 설정을 바탕으로 WebView 래퍼 APK를 추출하여 안드로이드에 설치하세요.")
    print("👉 PC 버전의 기능이 업데이트되면, 앱은 서버에서 데이터를 실시간으로 가져오므로")
    print("   앱을 매번 다시 깔 필요 없이 '자동 업데이트' 됩니다.")
    print("="*70 + "\n")

if __name__ == "__main__":
    generate_build_config()
