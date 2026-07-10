import asyncio
import os
import sys
from playwright.async_api import async_playwright

# Ensure output prints UTF-8
sys.stdout.reconfigure(encoding='utf-8')

class TikTokUploader:
    def __init__(self, session_dir=None):
        if session_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.session_dir = os.path.join(base_dir, "chrome_profile")
        else:
            self.session_dir = os.path.abspath(session_dir)
        
    async def upload_video(self, video_path, caption, wait_for_publish=True):
        """
        Uploads a video to TikTok using the stored session.
        video_path: Absolute path to the MP4 file.
        caption: Caption text including hashtags (e.g. "Cool video! #AI #TikTok")
        wait_for_publish: If True, actually clicks publish. Otherwise, stops before publishing for review.
        """
        video_path = os.path.abspath(video_path)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        print(f"[Uploader] Starting upload pipeline for: {video_path}")
        
        async with async_playwright() as p:
            # Launch persistent browser context to reuse the login session
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=False, # Must run headful to interact and avoid anti-bot checks
                viewport={"width": 1280, "height": 800},
                ignore_default_args=["--enable-automation"],
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--use-fake-ui-for-media-stream"
                ]
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            # Disable webdriver flag
            await page.add_init_script("const newProto = navigator.__proto__; delete newProto.webdriver; navigator.__proto__ = newProto;")
            
            # Go to Creator Center Upload Page
            upload_url = "https://www.tiktok.com/creator-center/upload?lang=ko-KR"
            print(f"[Uploader] Navigating to: {upload_url}")
            await page.goto(upload_url)
            
            # Wait for upload iframe or page elements
            # 로그인 여부 및 파일 업로드 요소 대기 루프 (자동 로그인 감지 대기)
            file_input = None
            print("[Uploader] 로그인 세션 유효성 확인 중...")
            
            for attempt in range(120): # 최대 10분 대기 (120 * 5초)
                try:
                    file_input = await page.wait_for_selector("input[type='file']", timeout=5000)
                    if file_input:
                        print("[Uploader] ✅ 로그인 세션 확인 완료! 자동 업로드를 계속 진행합니다.")
                        break
                except:
                    current_url = page.url
                    # 로그인 페이지로 리다이렉트되었거나 로그인 화면인 경우
                    if "login" in current_url:
                        if attempt % 3 == 0: # 15초마다 로그에 경고 메시지 인쇄
                            print("[Uploader] 🔑 로그인이 되어있지 않습니다. 화면에 나타난 크롬 브라우저에서 틱톡 로그인을 진행해 주세요.")
                            print("           로그인이 성공적으로 완료되면 파일 전송 및 게시가 자동으로 진행됩니다...")
                        await asyncio.sleep(5)
                    else:
                        # 일시적인 로딩 지연 대응
                        await asyncio.sleep(2)
            
            if not file_input:
                print("[Uploader] ❌ 로그인 대기 시간 초과 또는 파일 업로드 요소를 감지하지 못했습니다.")
                await context.close()
                return False
                
            # Upload the file
            print("[Uploader] Selected video file. Starting file transfer...")
            await file_input.set_input_files(video_path)
            print("[Uploader] File input complete. Waiting for processing...")
            
            # Wait for upload status / processing to complete
            # Usually, the editor/caption box becomes interactive or we wait for upload progress indicator to disappear
            await asyncio.sleep(10)
            
            # Fill caption
            print(f"[Uploader] Setting caption: {caption}")
            caption_selector = "div[contenteditable='true']"
            try:
                caption_elem = await page.wait_for_selector(caption_selector, timeout=20000)
                # Clear default name and type caption
                await caption_elem.click()
                # Select all and delete (Ctrl+A -> Backspace)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                # Type the caption text
                await caption_elem.type(caption)
                print("[Uploader] Caption set successfully.")
            except Exception as e:
                print(f"[Uploader] Failed to set caption: {e}")
                
            # Wait for video processing on TikTok server
            print("[Uploader] Waiting for video processing (30s)...")
            await asyncio.sleep(30)
            
            if wait_for_publish:
                print("[Uploader] Publishing video...")
                try:
                    # Look for publish button (게시 or Post)
                    post_button = await page.wait_for_selector("button:has-text('게시'), button:has-text('Post')", timeout=20000)
                    await post_button.click()
                    print("[Uploader] Publish button clicked successfully!")
                    await asyncio.sleep(5)
                except Exception as e:
                    print(f"[Uploader] Publish button click failed: {e}")
            else:
                print("[Uploader] Dry-run enabled. Skipping final publish click.")
                
            print("[Uploader] Closing browser context.")
            await context.close()
            return True
