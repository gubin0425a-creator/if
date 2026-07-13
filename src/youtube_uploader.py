import os
import pickle
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Ensure output prints UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Define scopes for YouTube upload
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class YouTubeUploader:
    def __init__(self):
        # Resolve paths relative to the project directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.client_secrets_file = os.path.join(base_dir, "client_secrets.json")
        self.credentials_pickle = os.path.join(base_dir, "youtube_token.pickle")
        self.credentials = None
        self.youtube_client = None

    def authenticate(self):
        """Loads credentials from pickle, or starts OAuth flow if they do not exist."""
        if os.path.exists(self.credentials_pickle):
            try:
                with open(self.credentials_pickle, 'rb') as token:
                    self.credentials = pickle.load(token)
            except Exception as e:
                print(f"[YouTube] 기존 토큰 로드 실패: {e}")

        # If there are no valid credentials, let the user log in
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    print("[YouTube] 토큰 만료됨. 새로고침 중...")
                    self.credentials.refresh(Request())
                except Exception as e:
                    print(f"[YouTube] 토큰 새로고침 실패: {e}")
                    self.credentials = None
            
            if not self.credentials:
                if not os.path.exists(self.client_secrets_file):
                    print("=" * 60)
                    print("[YouTube] ❌ client_secrets.json 파일이 프로젝트 루트 폴더에 없습니다!")
                    print("          구글 클라우드 콘솔(Google Cloud Console)에서 OAuth 클라이언트 ID 정보를")
                    print("          다운로드하여 'client_secrets.json' 이름으로 저장해 주세요.")
                    print("=" * 60)
                    raise FileNotFoundError("client_secrets.json not found in project root.")
                
                print("[YouTube] 브라우저를 열어 구글 유튜브 계정 로그인을 연동합니다...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file,
                    scopes=SCOPES
                )
                # Run local server to authenticate
                self.credentials = flow.run_local_server(
                    port=0,
                    authorization_prompt_message="구글 로그인을 완료해 주세요.",
                    success_message="유튜브 로그인 세션이 성공적으로 연동되었습니다! 이 창을 닫으셔도 됩니다."
                )
                
            # Save the credentials for next runs
            with open(self.credentials_pickle, 'wb') as token:
                pickle.dump(self.credentials, token)
                print("[YouTube] ✅ 새로운 유튜브 로그인 세션 토큰이 성공적으로 저장되었습니다!")

        self.youtube_client = build('youtube', 'v3', credentials=self.credentials)
        print("[YouTube] ✅ 유튜브 API 연동 완료!")
        return True

    def upload_shorts(self, video_path, title, description, tags=None, privacy_status="public"):
        """
        Uploads a video to YouTube with Shorts optimization.
        """
        if not self.youtube_client:
            self.authenticate()

        video_path = os.path.abspath(video_path)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        print(f"[YouTube] 업로드 시작: {os.path.basename(video_path)}")
        
        # Shorts 최적화를 위해 제목과 본문에 #Shorts 키워드 추가 강제
        if "#Shorts" not in title and "#shorts" not in title:
            title = f"{title[:90]} #Shorts"
        
        if "#Shorts" not in description and "#shorts" not in description:
            description = f"{description}\n\n#Shorts #history #whatif"

        if tags is None:
            tags = ["Shorts", "AlternativeHistory", "WhatIf", "Documentary"]

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '27'  # 27 = Education
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }

        # Chunked upload configuration
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024 * 1024  # 1MB chunks
        )

        request = self.youtube_client.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        print("[YouTube] 🎥 비디오 스트리밍 전송 중...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"[YouTube] 업로드 중: {int(status.progress() * 100)}%")

        video_id = response.get('id')
        print(f"[YouTube] 🎉 업로드 완료! Shorts ID: {video_id}")
        print(f"[YouTube] 🔗 링크: https://youtube.com/shorts/{video_id}")
        return video_id

if __name__ == "__main__":
    # Test authentication directly if executed
    uploader = YouTubeUploader()
    try:
        uploader.authenticate()
    except Exception as e:
        print(f"Auth test failed: {e}")
