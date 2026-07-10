"""
video_assembler.py
──────────────────
장면별 미디어(영상/이미지) + 나레이션 오디오 + 자막을 조립하여
최종 다큐멘터리 스타일 MP4를 완성하는 모듈.

핵심 기능:
  - 영상 클립: 원본 비디오에서 지정 duration만큼 잘라서 사용
  - 이미지 클립: Pillow로 자막 합성 후 Ken Burns 효과(줌+패닝) 적용
  - 단색 폴백: 미디어 없을 시 테마 색상 + 자막 카드 생성
  - 장면 전환: 크로스 페이드(cross-fade) 효과
  - 최종 합성: 나레이션 오디오 + 배경음악 (볼륨 덕킹)
"""
import os
import numpy as np
from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Pillow 10+ 호환성 패치 ────────────────────────────────────────────────────
# MoviePy 1.0.3는 PIL.Image.ANTIALIAS를 사용하지만 Pillow 10.0+에서 제거됨
# LANCZOS는 동일한 고품질 리샘플링 알고리즘
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS
# ─────────────────────────────────────────────────────────────────────────────

from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip,
    CompositeVideoClip, concatenate_videoclips,
    CompositeAudioClip
)
from moviepy.video.fx.fadein  import fadein
from moviepy.video.fx.fadeout import fadeout
from src.subtitle_renderer import draw_subtitle_on_image

RESOLUTION  = (1080, 1920)
FPS         = 30
CROSSFADE   = 0.5   # 크로스페이드 길이 (초)


# ── 켄 번스 효과 (AI 이미지 애니메이션화) ───────────────────────────────────────
def _ken_burns(img_path: str, duration: float, zoom_factor: float = 1.16, aspect_ratio: str = "9:16") -> ImageClip:
    """
    정지 이미지에 가감속(Easing)이 적용된 대각선 패닝과 줌인을 적용하여,
    마치 역동적인 3D 카메라 워킹 비디오 클립처럼 보이도록 Ken Burns 효과를 고도화합니다.
    """
    img = Image.open(img_path).convert("RGB")
    W, H = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)

    # 이미지를 target_ratio 비율보다 넉넉하게 크롭/리사이즈하여 패닝 마진을 확보합니다.
    img_ratio  = img.width / img.height
    target_ratio = W / H
    
    # 패닝 마진으로 1.25배 크게 리사이즈
    margin_factor = 1.25
    if img_ratio > target_ratio:
        new_h = int(H * margin_factor)
        new_w = int(H * margin_factor * img_ratio)
    else:
        new_w = int(W * margin_factor)
        new_h = int(W * margin_factor / img_ratio)
        
    img = img.resize((new_w, new_h), Image.LANCZOS)

    total_frames = int(duration * FPS)
    frames = []

    for f in range(total_frames):
        t = f / total_frames  # 0.0 ~ 1.0
        
        # 부드러운 가감속(Smoothstep Easing) 적용
        t_eased = t * t * (3.0 - 2.0 * t)
        
        # 줌인 배율 계산 (최대 zoom_factor)
        scale = 1.0 + (zoom_factor - 1.0) * t_eased
        sw = int(W / scale)
        sh = int(H / scale)
        max_dx = new_w - sw
        max_dy = new_h - sh
        
        # 부드러운 대각선 drift 적용 (단조로운 직선 패닝 탈피)
        cx = int(max_dx * 0.15) + int(max_dx * t_eased * 0.65)
        cy = int(max_dy * 0.1) + int(max_dy * t_eased * 0.5)
        cx = max(0, min(cx, new_w - sw))
        cy = max(0, min(cy, new_h - sh))
        crop = img.crop((cx, cy, cx + sw, cy + sh))
        frame = crop.resize((W, H), Image.LANCZOS)
        frames.append(np.array(frame))

    clip = ImageClip(np.array(frames[0])).set_duration(duration)

    def make_frame(t):
        idx = min(int(t * FPS), len(frames) - 1)
        return frames[idx]

    from moviepy.video.VideoClip import VideoClip
    kb_clip = VideoClip(make_frame, duration=duration)
    kb_clip = kb_clip.set_fps(FPS)
    return kb_clip


# ── 단색 배경 이미지 생성 ──────────────────────────────────────────────────
def _create_solid_bg(color_hex: str, subtitle: str, font_path: str,
                     is_hook: bool, lang: str, aspect_ratio: str = "9:16") -> Image.Image:
    """단색 배경에 자막을 합성한 PIL Image를 반환합니다."""
    # hex color → RGB
    color_hex = color_hex.lstrip("#")
    try:
        bg_color = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        bg_color = (26, 26, 46)
    W, H = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)
    base = Image.new("RGB", (W, H), color=bg_color)
    return draw_subtitle_on_image(base, subtitle, font_path, is_hook, lang, aspect_ratio)


# ── 장면 클립 생성 ─────────────────────────────────────────────────────────
def build_scene_clip(
    scene: dict,
    media: dict,
    audio_path: str,
    font_path: str,
    subtitle_lang: str = "ko",
    aspect_ratio: str = "9:16",
) -> VideoFileClip:
    # ── 씬 재생 시간을 오디오(나레이션) 길이에 칼같이 동기화 ───────────────────────
    duration = float(scene.get("duration_sec", 8))
    audio_clip = None
    if audio_path and os.path.exists(audio_path):
        try:
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration + 0.3 # 0.3초 미세 여유로 부드러운 전환
        except Exception as e:
            print(f"    [Assembler] 오디오 로딩 실패: {e}")

    subtitle    = scene.get(f"subtitle_{subtitle_lang}", scene.get("subtitle_ko", ""))
    bg_color    = scene.get("bg_color", "#1a1a2e")
    is_hook     = scene.get("is_hook", False)
    
    # 해상도 설정 분기
    W, H = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)

    media_type = media.get("type", "none")
    media_path = media.get("path")

    # ── A. 비디오 클립 ──────────────────────────────────────────────────────
    if media_type == "video" and media_path and os.path.exists(media_path):
        try:
            base_clip = VideoFileClip(media_path)

            # 비율 크롭 (9:16 또는 16:9)
            vid_ratio = base_clip.w / base_clip.h
            target_ratio = W / H
            if vid_ratio > target_ratio:
                # 가로형 영상: 높이 맞추고 좌우 크롭
                new_h = H
                new_w = int(H * vid_ratio)
            else:
                new_w = W
                new_h = int(W / vid_ratio)
            base_clip = base_clip.resize((new_w, new_h))
            # 중앙 크롭
            x1 = (new_w - W) // 2
            y1 = (new_h - H) // 2
            base_clip = base_clip.crop(x1=x1, y1=y1, x2=x1 + W, y2=y1 + H)

            # duration 조정
            if base_clip.duration < duration:
                # 짧으면 루프
                from moviepy.video.fx.loop import loop
                base_clip = loop(base_clip, duration=duration)
            else:
                base_clip = base_clip.subclip(0, duration)

            # 문장 단위 분할 로직
            import re
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', subtitle) if s.strip()]
            if not sentences:
                sentences = [subtitle]

            _font_path  = font_path
            _is_hook    = is_hook
            _lang       = subtitle_lang
            _ar         = aspect_ratio
            _duration   = duration

            def _burn_subtitle_at_t(get_frame, t, sentences=sentences, font=_font_path, hook=_is_hook, lang=_lang, ar=_ar, total_d=_duration):
                frame = get_frame(t)
                img = Image.fromarray(frame.copy())
                
                n = len(sentences)
                step = total_d / n
                idx = min(int(t / step), n - 1)
                curr_sub = sentences[idx]
                
                result = draw_subtitle_on_image(img, curr_sub, font, hook, lang, ar)
                return np.array(result)

            final_clip = base_clip.fl(_burn_subtitle_at_t)
            final_clip = final_clip.set_duration(duration)

        except Exception as e:
            print(f"    [Assembler] 비디오 클립 오류, 이미지 폴백: {e}")
            import traceback; traceback.print_exc()
            media_type = "none"

    # ── B. 이미지 클립 (Ken Burns) ──────────────────────────────────────────
    if media_type == "image" and media_path and os.path.exists(media_path):
        try:
            # 1. 자막이 없는 깨끗한 Ken Burns 비디오 클립 생성
            base_clip = _ken_burns(media_path, duration, aspect_ratio=aspect_ratio)
            
            # 문장 단위 분할 로직
            import re
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', subtitle) if s.strip()]
            if not sentences:
                sentences = [subtitle]

            _font  = font_path
            _hook  = is_hook
            _lang  = subtitle_lang
            _ar    = aspect_ratio
            _duration = duration

            def _burn_subtitle_at_t(get_frame, t, sentences=sentences, font=_font, hook=_hook, lang=_lang, ar=_ar, total_d=_duration):
                frame = get_frame(t)
                img = Image.fromarray(frame.copy())
                
                n = len(sentences)
                step = total_d / n
                idx = min(int(t / step), n - 1)
                curr_sub = sentences[idx]
                
                result = draw_subtitle_on_image(img, curr_sub, font, hook, lang, ar)
                return np.array(result)

            final_clip = base_clip.fl(_burn_subtitle_at_t)
            final_clip = final_clip.set_duration(duration)
        except Exception as e:
            print(f"    [Assembler] 이미지 클립 오류, 단색 폴백: {e}")
            media_type = "none"

    # ── C. 단색 폴백 ────────────────────────────────────────────────────────
    if media_type == "none":
        # Parse hex color to RGB tuple
        hex_color = bg_color.lstrip('#')
        try:
            rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            rgb_color = (26, 26, 46)
            
        base_img = Image.new("RGB", (W, H), color=rgb_color)
        base_clip = ImageClip(np.array(base_img)).set_duration(duration)
        
        # 문장 단위 분할 로직
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', subtitle) if s.strip()]
        if not sentences:
            sentences = [subtitle]

        _font  = font_path
        _hook  = is_hook
        _lang  = subtitle_lang
        _ar    = aspect_ratio
        _duration = duration

        def _burn_subtitle_at_t(get_frame, t, sentences=sentences, font=_font, hook=_hook, lang=_lang, ar=_ar, total_d=_duration):
            frame = get_frame(t)
            img = Image.fromarray(frame.copy())
            
            n = len(sentences)
            step = total_d / n
            idx = min(int(t / step), n - 1)
            curr_sub = sentences[idx]
            
            result = draw_subtitle_on_image(img, curr_sub, font, hook, lang, ar)
            return np.array(result)

        final_clip = base_clip.fl(_burn_subtitle_at_t)
        final_clip = final_clip.set_duration(duration)

    # ── 오디오 붙이기 ────────────────────────────────────────────────────────
    if audio_clip:
        final_clip = final_clip.set_audio(audio_clip)

    return final_clip.set_fps(FPS)


# ── 최종 영상 조립 ─────────────────────────────────────────────────────────
def assemble_final_video(
    scene_clips: list,
    output_path: str,
    bg_music_path: Optional[str] = None,
    music_volume: float = 0.15,
):
    """
    장면 클립 목록을 크로스페이드로 연결하고 배경음악을 믹싱합니다.
    """
    from typing import Optional

    print(f"  [Assembler] {len(scene_clips)}개 장면 클립 연결 중...")

    # ── 장면 전환: 클린 컷(Clean Cut) 사용 ──────────────────────────────────────
    # 기존 크로스페이드(CROSSFADE) 방식은 장면 전환 시 나레이션 오디오까지 같이 
    # 페이드인/아웃시켜 목소리가 웅얼거리거나 잘리는 어색한 버그를 유발했음.
    # 숏폼 다큐의 트렌디하고 스내피한 화면 구성을 위해 크로스페이드 없이 클린 컷으로 결합.
    final = concatenate_videoclips(scene_clips, method="compose")

    # 배경음악 믹싱
    if bg_music_path and os.path.exists(bg_music_path):
        try:
            music = AudioFileClip(bg_music_path)
            from moviepy.video.fx.loop import loop as audio_loop
            if music.duration < final.duration:
                # 루프
                loops = int(final.duration / music.duration) + 2
                from moviepy.audio.AudioClip import concatenate_audioclips
                music = concatenate_audioclips([music] * loops)
            music = music.subclip(0, final.duration).volumex(music_volume)

            if final.audio:
                combined = CompositeAudioClip([final.audio, music])
            else:
                combined = music
            final = final.set_audio(combined)
            print(f"  [Assembler] 🎵 배경음악 믹싱 완료 (볼륨 {int(music_volume*100)}%)")
        except Exception as e:
            print(f"  [Assembler] 배경음악 오류 (무시): {e}")

    print(f"  [Assembler] 🎬 최종 초고화질 인코딩 중... → {output_path}")
    threads = os.cpu_count() or 4
    
    # ── 표준적이고 100% 호환되는 CPU 멀티스레드 H.264 인코딩 적용 ─────────────────────
    # (GPU 가속인 h264_nvenc는 드라이버 매칭 실패 시 에러를 뿜지 않고 
    # 영상 트랙을 누락시킨 채 검은 화면만 빌드하는 치명적 버그가 존재하므로,
    # 100% 안정적이고 호환성이 완벽한 libx264 코덱을 기본으로 사용합니다.)
    try:
        print("  [Assembler] 🎬 CPU 고해상도 멀티스레드 인코딩 시작...")
        final.write_videofile(
            output_path,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="medium",                 # 디테일 복원과 속도의 최적 밸런스
            bitrate="15000k",                # 15Mbps 초고화질 비트레이트 지정
            threads=threads,
            ffmpeg_params=["-crf", "18", "-pix_fmt", "yuv420p"]      # CPU 기반 H.264 + 표준 YUV420p 픽셀 포맷 지정 (모바일/웹 재생 완벽)
        )
        print("  [Assembler] ✅ 비디오 렌더링 완료!")
    except Exception as e:
        print(f"  [Assembler] ❌ 인코딩 오류 발생: {e}")
        raise e
    return output_path
