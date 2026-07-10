"""
subtitle_renderer.py
─────────────────────
다국어 자막 생성 모듈
  - Pillow로 한국어/영어/일본어 자막을 이미지 위에 하드코딩
  - .SRT 자막 파일 저장 (유튜브/틱톡 첨부용)
  - Hook 장면: 화면 중앙 대형 강조 자막
  - 일반 장면: 화면 하단 다큐멘터리 스타일 자막
"""
import os
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

RESOLUTION = (1080, 1920)   # 9:16 세로 TikTok/Shorts 해상도

# 자막 위치 설정 (틱톡 하단 캡션/버튼 UI 영역에 가려지지 않도록 세이프존 높임)
SUBTITLE_BOTTOM_MARGIN = 500    # 화면 하단 마진
HOOK_CENTER_OFFSET     = 0      # 훅 자막: 화면 중앙 기준

FONT_COLORS = {
    "main":    (255, 255, 255),   # 흰색 나레이션 자막
    "hook":    (255, 220, 50),    # 노란색 훅 강조 자막
    "shadow":  (0, 0, 0),         # 검정 외곽선
}


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, lang: str = "ko") -> list[str]:
    """모든 언어에 대해 글자 단위로 줄 바꿈하여 일관된 렌더링을 보장합니다."""
    lines = []
    current = ""
    for char in text:
        test = current + char
        try:
            bbox = draw.textbbox((0, 0), test, font=font)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(test) * (font.size * 0.6)
        
        if w > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def draw_subtitle_on_image(
    base_image: Image.Image,
    subtitle_text: str,
    font_path: str,
    is_hook: bool = False,
    lang: str = "ko",
    aspect_ratio: str = "9:16",
) -> Image.Image:
    """
    PIL 이미지 위에 다큐멘터리 스타일 자막을 그려 반환합니다.
    훅 장면(is_hook=True): 화면 중앙 대형 강조 + 반투명 배경 박스
    일반 장면: 화면 하단 흰색 외곽선 자막
    """
    img = base_image.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    # 종횡비별 최적화된 폰트 크기 분기
    if aspect_ratio == "16:9":
        if is_hook:
            font_size = 60   # 16:9 훅: 가로 폭에 적합한 적정 대형 폰트
        else:
            font_size = 45   # 16:9 일반: 슬림하면서 가독성 높은 폰트
    else:
        if is_hook:
            font_size = 85   # 9:16 훅: 화면을 가득 채우는 대형 폰트
        else:
            font_size = 65   # 9:16 일반: 세로 화면 가독성을 위한 크기

    font = _load_font(font_path, font_size)
    max_text_width = W - 120

    lines = _wrap_text(draw, subtitle_text, font, max_text_width, lang)

    # 각 줄의 높이 계산
    line_height = font_size + 14
    
    line_data = []
    
    # 임시 계산용 ImageDraw (od는 캡슐을 그리지 않으므로 임시로 W 계산에만 사용)
    temp_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)

    if is_hook:
        # ── 훅 장면 Y축 배치 ──
        y_percent = 0.45 if aspect_ratio == "16:9" else 0.42
        curr_y = int(H * y_percent)
        
        for line in lines:
            try:
                bbox = temp_draw.textbbox((0, 0), line, font=font)
                lw = bbox[2] - bbox[0]
            except Exception:
                lw = len(line) * (font_size * 0.5)
            x = (W - lw) // 2
            
            line_data.append((line, x, curr_y, FONT_COLORS["hook"]))
            curr_y += line_height
    else:
        # ── 일반 장면 Y축 배치 ──
        curr_y = H - 150 if aspect_ratio == "16:9" else H - 680
        
        for line in lines:
            try:
                bbox = temp_draw.textbbox((0, 0), line, font=font)
                lw = bbox[2] - bbox[0]
            except Exception:
                lw = len(line) * (font_size * 0.5)
            x = (W - lw) // 2
            
            line_data.append((line, x, curr_y, FONT_COLORS["main"]))
            curr_y += line_height

    # 텍스트 그리기 (3D 입체 핑크 그림자 및 두꺼운 외곽선 효과 적용)
    # 그림자 색상: 숏츠 스타일 네온 핑크 (255, 64, 129)
    shadow_color = (255, 64, 129)
    
    if aspect_ratio == "16:9":
        offset = 4
        stroke_main = 5
        stroke_shadow = 3
    else:
        offset = 6
        stroke_main = 7
        stroke_shadow = 4

    # 오버레이 합성 레이어 (투명도 유지한 채 부드러운 드로잉)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    for line, x, y, color in line_data:
        # 1. 우하단 오프셋 위치에 핑크색 그림자 + 검은색 얇은 외곽선 먼저 렌더링
        od.text(
            (x + offset, y + offset),
            line,
            font=font,
            fill=shadow_color,
            stroke_width=stroke_shadow,
            stroke_fill=(0, 0, 0)
        )
        # 2. 본래 위치에 메인 색상(흰색/노란색) + 두꺼운 검은색 외곽선 덮어 씌우기
        od.text(
            (x, y), 
            line, 
            font=font, 
            fill=color, 
            stroke_width=stroke_main,
            stroke_fill=(0, 0, 0)
        )

    # 본 이미머지와 오버레이 합성
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


def generate_srt(scenes: list[dict], lang: str = "ko") -> str:
    """
    장면 목록으로 SRT 자막 파일 내용을 생성합니다.
    lang: 'ko', 'en', 'ja'
    """
    srt_lines = []
    timestamp = 0.0

    for i, scene in enumerate(scenes):
        duration = scene.get("duration_sec", 10)
        subtitle_key = f"subtitle_{lang}"
        subtitle = scene.get(subtitle_key, scene.get("subtitle_ko", ""))

        start_h = int(timestamp // 3600)
        start_m = int((timestamp % 3600) // 60)
        start_s = int(timestamp % 60)
        start_ms = int((timestamp % 1) * 1000)

        end_t = timestamp + duration
        end_h = int(end_t // 3600)
        end_m = int((end_t % 3600) // 60)
        end_s = int(end_t % 60)
        end_ms = int((end_t % 1) * 1000)

        srt_lines.append(str(i + 1))
        srt_lines.append(
            f"{start_h:02}:{start_m:02}:{start_s:02},{start_ms:03} --> "
            f"{end_h:02}:{end_m:02}:{end_s:02},{end_ms:03}"
        )
        srt_lines.append(subtitle)
        srt_lines.append("")

        timestamp += duration

    return "\n".join(srt_lines)


def save_srt_files(scenes: list[dict], output_dir: str, base_name: str):
    """KO / EN / JA 세 가지 SRT 파일을 저장합니다."""
    for lang in ["ko", "en", "ja"]:
        srt_content = generate_srt(scenes, lang)
        srt_path = os.path.join(output_dir, f"{base_name}_{lang}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        print(f"  [Subtitle] ✅ SRT 저장: {os.path.basename(srt_path)}")
