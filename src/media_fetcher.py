"""
media_fetcher.py
─────────────────
역사 이미지 / B-roll 영상 자동 수집 모듈
  1) Wikimedia Commons REST API  – 역사적 실제 사진, 삽화, 지도 (키 불필요, 무료)
  2) Pixabay API                – HD 비디오 클립 (무료 키 필요)
  3) Pexels API                 – HD 비디오 클립 (무료 키 필요)

우선순위:
  영상 → Pixabay → Pexels → Wikimedia 이미지(정지화면)
"""
import os
import io
import requests
import urllib.parse
from PIL import Image
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

_raw_pixabay = os.getenv("PIXABAY_API_KEY", "")
_raw_pexels  = os.getenv("PEXELS_API_KEY", "")

# 플레이스홀더 키는 유효하지 않으므로 빈 문자열 처리
PIXABAY_API_KEY = "" if (not _raw_pixabay or "your_" in _raw_pixabay) else _raw_pixabay
PEXELS_API_KEY  = "" if (not _raw_pexels  or "your_" in _raw_pexels)  else _raw_pexels

HEADERS = {"User-Agent": "TikTokAutoBot/2.0 (educational research)"}


# ─────────────────────────────────────────────────────────────────────────────
# Wikimedia Commons – 이미지 검색
# ─────────────────────────────────────────────────────────────────────────────
def fetch_wikimedia_image(query: str, save_path: str) -> bool:
    """
    Wikimedia Commons에서 역사 이미지를 검색하여 다운로드합니다.
    반환: 성공 여부
    """
    ALLOWED_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    BLOCKED_EXTS = (".pdf", ".svg", ".tif", ".tiff", ".xcf", ".ogg", ".ogv", ".webm", ".mp4")
    try:
        search_url = "https://commons.wikimedia.org/w/api.php"
        # 검색어에 이미지 파일 타입만 반환되도록 필터 추가
        params = {
            "action": "query",
            "list": "search",
            "srsearch": f"filetype:bitmap {query}",
            "srnamespace": "6",
            "srlimit": "20",
            "format": "json",
        }
        resp = requests.get(search_url, params=params, headers=HEADERS, timeout=12)
        data = resp.json()
        results = data.get("query", {}).get("search", [])

        if not results:
            # fallback: 필터 없이 재시도
            params["srsearch"] = query
            resp = requests.get(search_url, params=params, headers=HEADERS, timeout=12)
            results = resp.json().get("query", {}).get("search", [])

        if not results:
            print(f"    [Wikimedia] '{query}' 검색 결과 없음")
            return False

        # 허용 확장자 파일만 선택, 차단 확장자 제외
        file_title = None
        for r in results:
            title = r.get("title", "")
            title_lower = title.lower()
            if any(title_lower.endswith(ext) for ext in BLOCKED_EXTS):
                continue
            if any(title_lower.endswith(ext) for ext in ALLOWED_EXTS):
                file_title = title
                break

        if not file_title:
            print(f"    [Wikimedia] 허용된 이미지 파일 없음")
            return False

        # imageinfo API로 썸네일 URL 가져오기
        info_params = {
            "action": "query",
            "titles": file_title,
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "iiurlwidth": "1080",
            "format": "json",
        }
        info_resp = requests.get(search_url, params=info_params, headers=HEADERS, timeout=12)
        info_data = info_resp.json()
        pages = info_data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                continue
            imageinfo = page.get("imageinfo", [])
            if not imageinfo:
                continue
            mime = imageinfo[0].get("mime", "")
            if not mime.startswith("image/"):
                continue
            img_url = imageinfo[0].get("thumburl") or imageinfo[0].get("url", "")
            if not img_url:
                continue
            img_resp = requests.get(img_url, headers=HEADERS, timeout=25)
            if img_resp.status_code == 200 and len(img_resp.content) > 5000:
                with open(save_path, "wb") as f:
                    f.write(img_resp.content)
                print(f"    [Wikimedia] ✅ 이미지 저장: {os.path.basename(save_path)} ({len(img_resp.content)//1024}KB)")
                return True

        print(f"    [Wikimedia] URL 추출 실패: {file_title}")
        return False
    except Exception as e:
        print(f"    [Wikimedia] 오류: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Pixabay – 영상 검색
# ─────────────────────────────────────────────────────────────────────────────
def fetch_pixabay_video(query: str, save_path: str) -> bool:
    """Pixabay에서 b-roll 영상을 검색하고 다운로드합니다."""
    if not PIXABAY_API_KEY:
        return False
    try:
        url = "https://pixabay.com/api/videos/"
        params = {
            "key": PIXABAY_API_KEY,
            "q": query,
            "per_page": 5,
            "video_type": "film",
            "safesearch": "true",
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        hits = data.get("hits", [])
        if not hits:
            print(f"    [Pixabay] '{query}' 영상 없음")
            return False

        # 작은 용량의 small/medium 파일 선택
        video_url = None
        for hit in hits:
            videos = hit.get("videos", {})
            for size in ["small", "medium", "large"]:
                v = videos.get(size, {})
                url_candidate = v.get("url")
                if url_candidate:
                    video_url = url_candidate
                    break
            if video_url:
                break

        if not video_url:
            return False

        vresp = requests.get(video_url, headers=HEADERS, timeout=60, stream=True)
        with open(save_path, "wb") as f:
            for chunk in vresp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"    [Pixabay] ✅ 영상 저장: {os.path.basename(save_path)}")
        return True
    except Exception as e:
        print(f"    [Pixabay] 오류: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Pexels – 영상 검색 (Pixabay 실패 시 대안)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_pexels_video(query: str, save_path: str, aspect_ratio: str = "9:16") -> bool:
    """Pexels에서 b-roll 영상을 검색하고 다운로드합니다."""
    if not PEXELS_API_KEY:
        return False
    try:
        headers = {**HEADERS, "Authorization": PEXELS_API_KEY}
        url = "https://api.pexels.com/videos/search"
        orientation = "portrait" if aspect_ratio == "9:16" else "landscape"
        params = {"query": query, "per_page": 5, "orientation": orientation}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        videos = data.get("videos", [])
        if not videos:
            print(f"    [Pexels] '{query}' 영상 없음")
            return False

        # 가장 작은 video file 선택 (빠른 다운로드)
        video_files = videos[0].get("video_files", [])
        video_files_sorted = sorted(video_files, key=lambda x: x.get("width", 9999))
        for vf in video_files_sorted:
            if vf.get("quality") in ["sd", "hd"]:
                video_url = vf.get("link")
                if video_url:
                    vresp = requests.get(video_url, headers=HEADERS, timeout=60, stream=True)
                    with open(save_path, "wb") as f:
                        for chunk in vresp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"    [Pexels] ✅ 영상 저장: {os.path.basename(save_path)}")
                    return True
        return False
    except Exception as e:
        print(f"    [Pexels] 오류: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# AI 이미지 생성 (Imagen 3 우선 → Gemini 2.0 Flash Image 폴백)
# ─────────────────────────────────────────────────────────────────────────────
def generate_ai_image(prompt: str, save_path: str, aspect_ratio: str = "9:16") -> bool:
    """
    Imagen 4를 우선 사용하여 초고화질 실사 이미지를 생성합니다.
    실패 시 gemini-3.1-flash-image 로 폴백합니다.
    """
    try:
        from src.topic_recommender import _get_client
        client = _get_client()
        
        comp = "cinematic landscape 16:9 composition" if aspect_ratio == "16:9" else "vertical 9:16 portrait composition"
        # ── 극실사 품질 프롬프트 엔지니어링 ──
        enhanced_prompt = (
            f"{prompt}. "
            f"Ultra-photorealistic, 8K UHD, cinematic DSLR photography, shot on 85mm prime lens f/1.8, "
            f"natural subsurface skin scattering, pore-level skin detail, dramatic documentary lighting, "
            f"historically accurate costumes and settings, "
            f"{comp}, cinematic color grading, "
            f"National Geographic documentary style"
        )
        
        # ── 1순위: Imagen 4 (최고 실사 품질) ──
        try:
            print(f"    [AI Media] [INFO] Imagen 4 실사 이미지 생성 중...")
            from google.genai import types as genai_types
            imagen_response = client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=enhanced_prompt,
                config=genai_types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    output_mime_type='image/jpeg'
                )
            )
            if imagen_response.generated_images:
                img_data = imagen_response.generated_images[0].image.image_bytes
                with open(save_path, "wb") as f:
                    f.write(img_data)
                print(f"    [AI Media] [SUCCESS] Imagen 4 이미지 생성 완료: {os.path.basename(save_path)} ({len(img_data)//1024}KB)")
                return True
        except Exception as img_err:
            print(f"    [AI Media] [WARN] Imagen 4 실패 ({img_err}), Gemini Flash 폴백...")
        
        # ── 2순위: Gemini 3.1 Flash Image (폴백) ──
        print(f"    [AI Media] [INFO] Gemini Flash 이미지 생성 중...")
        response = client.models.generate_content(
            model='gemini-3.1-flash-image',
            contents=enhanced_prompt,
            config={'responseModalities': ['IMAGE', 'TEXT']}
        )
        
        for candidate in (response.candidates or []):
            for part in (candidate.content.parts or []):
                if part.inline_data:
                    data_bytes = part.inline_data.data
                    with open(save_path, "wb") as f:
                        f.write(data_bytes)
                    print(f"    [AI Media] [SUCCESS] Gemini Flash 이미지 생성 완료: {os.path.basename(save_path)} ({len(data_bytes)//1024}KB)")
                    return True
        return False
    except Exception as e:
        print(f"    [AI Media] [ERROR] 이미지 생성 실패: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Pixabay / Pexels – 이미지 검색 (고증 레퍼런스 수집용)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_pixabay_image(query: str, save_path: str) -> bool:
    """Pixabay에서 실제 사진 레퍼런스를 검색하고 다운로드합니다."""
    if not PIXABAY_API_KEY:
        return False
    try:
        url = "https://pixabay.com/api/"
        params = {
            "key": PIXABAY_API_KEY,
            "q": query,
            "image_type": "photo",
            "safesearch": "true",
            "per_page": 5,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        hits = data.get("hits", [])
        if not hits:
            return False
        img_url = hits[0].get("webformatURL") or hits[0].get("largeImageURL")
        if img_url:
            img_resp = requests.get(img_url, headers=HEADERS, timeout=20)
            if img_resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(img_resp.content)
                print(f"    [Pixabay Reference] ✅ 고증 사진 다운로드 완료: {os.path.basename(save_path)}")
                return True
        return False
    except Exception as e:
        print(f"    [Pixabay Reference] 오류: {e}")
        return False


def fetch_pexels_image(query: str, save_path: str) -> bool:
    """Pexels에서 실제 사진 레퍼런스를 검색하고 다운로드합니다."""
    if not PEXELS_API_KEY:
        return False
    try:
        headers = {**HEADERS, "Authorization": PEXELS_API_KEY}
        url = "https://api.pexels.com/v1/search"
        params = {"query": query, "per_page": 5}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        photos = data.get("photos", [])
        if not photos:
            return False
        img_url = photos[0].get("src", {}).get("large") or photos[0].get("src", {}).get("original")
        if img_url:
            img_resp = requests.get(img_url, headers=HEADERS, timeout=20)
            if img_resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(img_resp.content)
                print(f"    [Pexels Reference] ✅ 고증 사진 다운로드 완료: {os.path.basename(save_path)}")
                return True
        return False
    except Exception as e:
        print(f"    [Pexels Reference] 오류: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 고증 사진 기반 AI 영상 프레임 생성 (Multimodal Img2Prompt → Txt2Img)
# ─────────────────────────────────────────────────────────────────────────────
def generate_ai_image_from_reference(ref_image_path: str, base_prompt: str, save_path: str, aspect_ratio: str = "9:16") -> bool:
    """
    수집된 역사적 고증 사진(Wikimedia/Pixabay/Pexels)을 분석하여 구조, 인물, 분위기를 유지한
    고화질 9:16 또는 16:9 극실사 AI 이미지(비디오 프레임)로 새롭게 렌더링(재창조)합니다.
    """
    try:
        import json
        from src.topic_recommender import _get_client
        client = _get_client()
        
        # 1. Pillow로 레퍼런스 이미지 로드
        from PIL import Image as PILImage
        ref_image = PILImage.open(ref_image_path)
        
        # 2. Gemini 2.5 Flash를 이용한 멀티모달 이미지 분석 및 영화적 프롬프트 도출
        print(f"    [AI Transform] 🔍 고증 역사 사진 분석 중 (레퍼런스: {os.path.basename(ref_image_path)})...")
        analysis_prompt = (
            f"Analyze this historical reference image in detail, focusing on the main figures, composition, "
            f"clothing, objects, background environment, and historical details. "
            f"Based on this analysis, generate a highly detailed and cinematic English image generation prompt "
            f"that will recreate a modern, photorealistic, high-fidelity version of this exact scene. "
            f"The prompt must preserve the core composition and historical elements of this reference image. "
            f"Scene context: '{base_prompt}'. "
            f"Respond ONLY with the final prompt string inside a JSON block like: {{\"prompt\": \"your cinematic prompt here\"}}."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[ref_image, analysis_prompt],
        )
        
        # JSON 응답 파싱 및 정제
        raw_text = response.text.strip()
        if "```" in raw_text:
            parts = raw_text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                try:
                    parsed = json.loads(part)
                    enhanced_prompt = parsed.get("prompt", base_prompt)
                    break
                except Exception:
                    continue
        else:
            try:
                parsed = json.loads(raw_text)
                enhanced_prompt = parsed.get("prompt", base_prompt)
            except Exception:
                enhanced_prompt = base_prompt
                
        print(f"    [AI Transform] [INFO] 고증기반 향상된 프롬프트 도출 완료.")
        
        comp = "cinematic landscape 16:9 composition" if aspect_ratio == "16:9" else "vertical 9:16 portrait composition"
        # 3. Imagen 4 우선 → Gemini 3.1 Flash Image 폴백으로 고화질 AI 이미지 생성
        final_enhanced_prompt = (
            f"{enhanced_prompt}. "
            f"Ultra-photorealistic, 8K UHD, cinematic DSLR photography, "
            f"historically accurate details, {comp}, "
            f"dramatic documentary lighting, National Geographic style"
        )
        
        print(f"    [AI Transform] [INFO] 고증기반 실사 AI 이미지 생성 중...")
        
        # Imagen 4 우선 시도
        try:
            from google.genai import types as genai_types
            imagen_response = client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=final_enhanced_prompt,
                config=genai_types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    output_mime_type='image/jpeg'
                )
            )
            if imagen_response.generated_images:
                img_data = imagen_response.generated_images[0].image.image_bytes
                with open(save_path, "wb") as f:
                    f.write(img_data)
                print(f"    [AI Transform] [SUCCESS] Imagen 4 고증 이미지 완료: {os.path.basename(save_path)} ({len(img_data)//1024}KB)")
                return True
        except Exception:
            pass
        
        # Gemini Flash 폴백
        image_response = client.models.generate_content(
            model='gemini-3.1-flash-image',
            contents=final_enhanced_prompt,
            config={'responseModalities': ['IMAGE', 'TEXT']}
        )
        
        for candidate in (image_response.candidates or []):
            for part in (candidate.content.parts or []):
                if part.inline_data:
                    data_bytes = part.inline_data.data
                    with open(save_path, "wb") as f:
                        f.write(data_bytes)
                    print(f"    [AI Transform] [SUCCESS] Gemini Flash 고증 이미지 완료: {os.path.basename(save_path)} ({len(data_bytes)//1024}KB)")
                    return True
        return False
    except Exception as e:
        print(f"    [AI Transform] [WARN] 레퍼런스 기반 생성 실패 ({e}). 기본 AI 생성으로 전환합니다.")
        return False


def generate_ai_video(prompt: str, save_path: str, duration_sec: int = 6, aspect_ratio: str = "9:16") -> bool:
    """
    Google Veo API (veo-3.1-generate-preview)를 이용해 9:16 또는 16:9 AI 비디오를 생성합니다.
    """
    import time
    try:
        from src.topic_recommender import _get_client
        from google.genai import types as genai_types
        client = _get_client()
        
        comp = "cinematic landscape 16:9 composition" if aspect_ratio == "16:9" else "vertical 9:16 portrait composition"
        # Veo 가이드라인에 따른 최적화 프롬프트 덧붙임
        enhanced_prompt = (
            f"{prompt}. Cinematic 8K video, hyperrealistic detail, sunset golden hour lighting, "
            f"masterpiece, National Geographic style, professional camera panning movement, {comp}"
        )
        
        # duration은 Veo가 허용하는 4~8초 범위로 강제 조정
        clamped_duration = max(4, min(8, int(duration_sec)))
        
        print(f"    [Veo Video] [INFO] Veo AI 비디오 생성 시작 (Model: veo-3.1-generate-preview, {clamped_duration}초, 비율: {aspect_ratio})...")
        
        operation = client.models.generate_videos(
            model='veo-3.1-generate-preview',
            prompt=enhanced_prompt,
            config=genai_types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                duration_seconds=clamped_duration,
            )
        )
        
        print(f"    [Veo Video] [INFO] 비디오 작업 생성 완료 (LRO: {operation.name}). 폴링 대기 중...")
        
        # 폴링 루프
        start_time = time.time()
        while not operation.done:
            time.sleep(10)
            print(f"    [Veo Video] [INFO] 비디오 렌더링 진행 중... ({int(time.time() - start_time)}초)")
            operation = client.operations.get(operation)
            
        print(f"    [Veo Video] [INFO] 비디오 생성 성공! 결과 다운로드 중...")
        result = operation.result
        generated_video = result.generated_videos[0]
        video_bytes = client.files.download(file=generated_video.video)
        
        with open(save_path, "wb") as f:
            f.write(video_bytes)
        print(f"    [Veo Video] [SUCCESS] Veo 비디오 생성 및 저장 완료: {os.path.basename(save_path)} ({len(video_bytes)//1024}KB)")
        return True
    except Exception as e:
        print(f"    [Veo Video] [ERROR] 비디오 생성 오류 발생: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 통합 미디어 페처 (고증 사진 수집 우선 → 고증 이미지 기반 AI 재생성)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_scene_media(scene: dict, scene_index: int, temp_dir: str, media_type: str = "image", aspect_ratio: str = "9:16") -> dict:
    """
    장면 데이터로부터 영상 또는 이미지를 수집/생성합니다.
    media_type: "image" (기본 이미지+Ken Burns) 또는 "video" (AI 동영상)
    aspect_ratio: "9:16" (세로형) 또는 "16:9" (가로형)
    """
    image_query = scene.get("image_query", "")
    video_query = scene.get("video_query", "")
    duration_sec = scene.get("duration_sec", 6)
    
    ref_image_path = os.path.join(temp_dir, f"scene_ref_{scene_index}.jpg")
    final_image_path = os.path.join(temp_dir, f"scene_media_{scene_index}.jpg")
    final_video_path = os.path.join(temp_dir, f"scene_media_{scene_index}.mp4")
    
    # ── [동영상(video) 모드인 경우] ──
    if media_type == "video":
        print(f"    [Media] [INFO] 비디오 모드 구동 중 (Scene {scene_index + 1})")
        # 1. Pixabay/Pexels 에서 B-roll 영상 소스 우선 검색 (가장 빠름)
        if video_query:
            print(f"    [Media] [INFO] 1단계: B-roll 비디오 검색 중: '{video_query}'...")
            if fetch_pixabay_video(video_query, final_video_path):
                return {"type": "video", "path": final_video_path}
            elif fetch_pexels_video(video_query, final_video_path, aspect_ratio):
                return {"type": "video", "path": final_video_path}
                
        # 2. Google Veo AI 동영상 생성 시도
        if image_query:
            print(f"    [Media] [INFO] 2단계: Google Veo AI 동영상 생성 시도...")
            if generate_ai_video(image_query, final_video_path, duration_sec, aspect_ratio):
                return {"type": "video", "path": final_video_path}
            else:
                print(f"    [Media] [WARN] Veo 동영상 생성 실패. 이미지 생성 방식으로 폴백합니다.")
        
        # 3. 비디오 생성이 실패하거나 없을 경우 이미지 모드로 자연 폴백(Fallback) 진행!
        # (이미지가 리턴되면 video_assembler가 알아서 Ken Burns 효과를 주어 결합합니다.)

    # ── [기본 이미지(image) 모드 또는 비디오 생성 실패 폴백인 경우] ──
    # 1단계: 실제 역사 고증 사진/유물/지도 검색 (Wikimedia -> Pixabay -> Pexels)
    has_ref = False
    if image_query:
        print(f"    [Media] [INFO] 1단계: 고증 레퍼런스 자료 검색 중: '{image_query}'...")
        if fetch_wikimedia_image(image_query, ref_image_path):
            has_ref = True
        elif fetch_pixabay_image(image_query, ref_image_path):
            has_ref = True
        elif fetch_pexels_image(image_query, ref_image_path):
            has_ref = True
            
    # 2단계: 고증 레퍼런스가 존재할 시 해당 이미지를 기반으로 Gemini AI 동영상(프레임) 생성
    if has_ref:
        print(f"    [Media] [INFO] 2단계: 실제 고증 사진을 기반으로 Gemini AI 비디오 프레임 재생성 시도...")
        if generate_ai_image_from_reference(ref_image_path, image_query, final_image_path, aspect_ratio):
            # 사용이 끝난 레퍼런스 파일 삭제
            if os.path.exists(ref_image_path):
                try: os.remove(ref_image_path)
                except: pass
            return {"type": "image", "path": final_image_path}
            
    # 3단계: 고증 레퍼런스가 부재할 시 기본 프롬프트를 사용하여 AI 이미지로 대체 창작
    if image_query:
        print(f"    [Media] [INFO] 3단계: 고증 사진 없음 → 프롬프트 기반 기본 AI 이미지 생성...")
        if generate_ai_image(image_query, final_image_path, aspect_ratio):
            return {"type": "image", "path": final_image_path}

    # 최후 폴백: None (black background 사용)
    print(f"    [Media] [WARN] 장면 {scene_index + 1}: 미디어 수집 실패 → 단색 배경 사용")
    return {"type": "none", "path": None}
