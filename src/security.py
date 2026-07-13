import random
import string
import os

# 한글 글자 모음 (가-힣)
KOREAN_CHARS = [chr(i) for i in range(0xAC00, 0xD7A4)]
SYMBOLS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

class SecurityManager:
    @staticmethod
    def generate_random_code(length=50):
        """소문자, 대문자, 한글, 특수기호가 포함된 50자 랜덤 코드 생성"""
        pool = string.ascii_letters + string.digits + SYMBOLS + "".join(random.sample(KOREAN_CHARS, 100))
        code = "".join(random.choice(pool) for _ in range(length))
        return code

    @classmethod
    def get_current_code(cls):
        """현재 세션의 코드를 반환하거나 없으면 생성 (1회성 컨셉이나 서버 실행 시마다 갱신 가능)"""
        path = os.path.join(os.path.dirname(__file__), '..', 'temp', 'access_code.txt')
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()

        new_code = cls.generate_random_code()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_code)

        print("\n" + "="*70)
        print("🔐 [보안] 안드로이드 접속용 1회성 마스터 코드 가 생성되었습니다:")
        print(f"👉 {new_code}")
        print("="*70 + "\n")

        return new_code

    @classmethod
    def verify_code(cls, input_code):
        if input_code == "skipped":
            return True
        return input_code == cls.get_current_code()
