import os
import sys
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Ensure utf-8 encoding for standard output
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    client_secrets_path = os.path.join(base_dir, 'client_secrets.json')
    token_path = os.path.join(base_dir, 'token.pickle')
    
    print("==================================================================")
    print("유튜브 자동 업로드 인증 세션(token.pickle) 기동 헬퍼")
    print("==================================================================")
    
    if not os.path.exists(client_secrets_path):
        print(f"\n[오류] client_secrets.json 파일을 찾을 수 없습니다.")
        print(f"경로를 확인해 주세요: {client_secrets_path}")
        return

    creds = None
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            print(f"기존 토큰 로드 실패: {e}")

    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                print("\n[OAuth] 만료된 토큰을 갱신 중입니다...")
                creds.refresh(Request())
            else:
                print("\n[OAuth] 웹 브라우저를 열어 구글 본인 인증 로그인을 개시합니다...")
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            print("\n[OAuth] ✅ token.pickle 인증서가 생성 및 저장되었습니다!")
            print("이제 유튜브 자동 업로드를 100% 무인으로 실행하실 수 있습니다.")
        except Exception as e:
            print(f"\n[OAuth 인증 에러]: {e}")
    else:
        print("\n[OAuth] ✅ 이미 유효한 token.pickle 인증 토큰이 존재합니다. 바로 업로드 가능합니다.")

if __name__ == '__main__':
    main()
