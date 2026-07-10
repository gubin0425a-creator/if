import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    session_dir = "./chrome_profile"
    
    if not os.path.exists(session_dir):
        print("Profile directory does not exist.")
        return
        
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=True
        )
        
        page = await context.new_page()
        await page.goto("https://www.tiktok.com/")
        await page.wait_for_timeout(3000) # wait for page load
        
        # Check if we are logged in by searching for user profile elements or login button
        login_btn = await page.query_selector("button:has-text('로그인')")
        login_btn_en = await page.query_selector("button:has-text('Log in')")
        
        cookies = await context.cookies()
        session_cookies = [c for c in cookies if 'session' in c['name'].lower() or 'auth' in c['name'].lower() or 'sid' in c['name'].lower()]
        
        print(f"Total cookies stored: {len(cookies)}")
        print(f"Session-related cookies: {[c['name'] for c in session_cookies]}")
        
        if login_btn or login_btn_en:
            print("Status: NOT LOGGED IN (Login button detected)")
        else:
            # Check if profile icon or specific avatar is present
            avatar = await page.query_selector("[data-e2e='profile-icon']")
            if avatar:
                print("Status: LOGGED IN (Profile icon detected!)")
            else:
                print("Status: UNCERTAIN (No login button and no profile icon)")
                
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
