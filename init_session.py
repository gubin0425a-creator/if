import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    session_dir = os.path.join(base_dir, "chrome_profile")
    
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        
    print("==================================================================")
    print("틱톡 로그인 세션 초기화 스크립트 (우회 옵션 적용)")
    print("==================================================================")
    
    async with async_playwright() as p:
        # Launch persistent context with stealth arguments to prevent Google/TikTok bot detection
        context = await p.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=False,
            viewport={"width": 1280, "height": 800},
            ignore_default_args=["--enable-automation"], # Hide "Chrome is being controlled" banner
            args=[
                "--disable-blink-features=AutomationControlled", # Bypass basic bot detection
                "--use-fake-ui-for-media-stream"
            ]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Override navigator.webdriver to false
        await page.add_init_script("const newProto = navigator.__proto__; delete newProto.webdriver; navigator.__proto__ = newProto;")
        
        # Reconfigure sys.stdout to handle Unicode if possible
        try:
            import sys
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
            
        print("\n[Session] Browser launched. Moving to TikTok...")
        await page.goto("https://www.tiktok.com/")
        
        print("\n[Session] Please complete login in the browser window, then close the window to save session automatically.")
        
        # 사용자가 브라우저 창을 완전히 닫거나 크롬이 종료될 때까지 Event로 안전하게 대기
        closed_event = asyncio.Event()
        context.on("close", lambda ctx: closed_event.set())
        
        # 페이지가 닫힐 때 남은 페이지가 없으면 이벤트를 트리거합니다.
        def page_closed():
            if len(context.pages) == 0:
                closed_event.set()
                
        for p in context.pages:
            p.on("close", lambda page: page_closed())
            
        # 새 페이지가 열리거나 닫힐 때를 대비
        context.on("page", lambda p: p.on("close", lambda page: page_closed()))
        
        try:
            await closed_event.wait()
        except:
            pass
                
        await context.close()
        print("\n[Session] ✅ 로그인 세션이 성공적으로 저장되었습니다!")

if __name__ == "__main__":
    asyncio.run(main())
