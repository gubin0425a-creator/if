import os
import sys
import json
import asyncio
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Project Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "videos_to_upload")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
FONT_PATH = os.path.join(BASE_DIR, "NanumGothicBold.ttf")
RESOLUTION = (1080, 1920) # vertical 9:16 aspect ratio

# Ensure directories exist
for d in [INPUT_DIR, TEMP_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

def download_font():
    """Downloads NanumGothicBold.ttf if not present"""
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
    if not os.path.exists(FONT_PATH):
        print("📥 폰트 파일(NanumGothicBold.ttf)이 없습니다. 다운로드를 시작합니다...")
        try:
            r = requests.get(font_url, timeout=30)
            r.raise_for_status()
            with open(FONT_PATH, "wb") as f:
                f.write(r.content)
            print("✅ 폰트 다운로드 완료!")
        except Exception as e:
            print(f"❌ 폰트 다운로드 실패: {e}")
            print("⚠️ 기본 시스템 폰트를 사용합니다. (화질/자막 정렬이 달라질 수 있습니다.)")

def create_text_image(text, bg_color, output_path, font_size=55):
    """
    Renders wrapped text on a solid color image using Pillow.
    Bypasses MoviePy's ImageMagick dependency on Windows.
    """
    img = Image.new('RGB', RESOLUTION, color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Load font
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()
        
    # Wrap text to fit inside 900px width
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        try:
            bbox = draw.textbbox((0, 0), line_str, font=font)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(line_str) * (font_size * 0.6) # fallback estimation
            
        if w > RESOLUTION[0] - 180: # Max width limit
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))
        
    # Calculate text positioning and line heights
    line_heights = []
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])
        except Exception:
            line_heights.append(font_size + 10)
            
    total_height = sum(line_heights) + (len(lines) - 1) * 20
    
    # Vertically center the text box
    y = (RESOLUTION[1] - total_height) // 2
    
    # Draw semi-transparent background card for text readability
    padding = 40
    box_y0 = y - padding
    box_y1 = y + total_height + padding
    
    # Draw card
    draw.rectangle([80, box_y0, RESOLUTION[0] - 80, box_y1], fill=(0, 0, 0, 190))
    
    # Draw each line of text
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except Exception:
            w = len(line) * (font_size * 0.5)
            h = font_size
            
        x = (RESOLUTION[0] - w) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += h + 20
        
    img.save(output_path)

async def generate_tts(text, output_path, voice="ko-KR-InJoonNeural"):
    """Generates speech audio file from text using Edge-TTS"""
    communicate = edge_tts.Communicate(text, voice, rate="+30%")
    await communicate.save(output_path)

def generate_script(api_key, topic):
    """Generates JSON formatted story scenes using Gemini API"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    prompt = f"""
당신은 틱톡 쇼츠 대본 작가입니다. 
다음 주제로 5개의 장면(Scene)으로 구성된 흥미진진한 1분 미만 숏폼 대본을 작성해주세요.
각 장면의 나레이션은 한국어로 자연스럽고 몰입감 있게 작성해야 합니다.
주제: {topic}

반드시 아래 JSON 배열 형식으로만 출력하세요. 다른 마크다운 설명이나 텍스트는 절대 포함하지 마세요.
[
  {{"text": "첫 번째 장면 나레이션 (15자 이내의 짧은 훅)", "color": "#1a1a2e"}},
  {{"text": "두 번째 장면 나레이션", "color": "#16213e"}},
  {{"text": "세 번째 장면 나레이션", "color": "#0f3460"}},
  {{"text": "네 번째 장면 나레이션", "color": "#1a1a2e"}},
  {{"text": "다섯 번째 장면 나레이션", "color": "#53354a"}}
]
"""
    print("📝 Gemini AI로 대본을 생성하고 있습니다...")
    response = model.generate_content(prompt)
    
    response_text = response.text.strip()
    
    # Strip markdown code block wrappers if any
    if response_text.startswith("```json"):
        response_text = response_text[7:-3]
    elif response_text.startswith("```"):
        response_text = response_text[3:-3]
        
    return json.loads(response_text.strip())

async def run_pipeline(topic=None):
    # Load API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or "your_" in api_key or "여기에_" in api_key:
        print("❌ 에러: .env 파일에서 'GEMINI_API_KEY'를 찾을 수 없거나 올바르지 않습니다.")
        print("구글 AI 스튜디오(https://aistudio.google.com/)에서 API 키를 발급받아 .env 파일에 등록해 주세요.")
        return
        
    if not topic:
        topic = "이순신 장군이 명량해전에서 패배했다면 조선은 어떻게 되었을까?"
        
    print("==================================================================")
    print(f"🎬 틱톡 자동 숏폼 영상 생성 시작: '{topic}'")
    print("==================================================================")
    
    download_font()
    
    # 1. Generate script
    try:
        script_data = generate_script(api_key, topic)
        print("✅ 대본 및 테마 색상 설정 완료!")
    except Exception as e:
        print(f"❌ 대본 생성 실패: {e}")
        return
        
    clips = []
    temp_files = []
    
    print("\n🎧 장면별 오디오 및 비주얼 합성 중...")
    for i, scene in enumerate(script_data):
        text = scene["text"]
        bg_color = scene.get("color", "#1a1a2e")
        
        audio_path = os.path.join(TEMP_DIR, f"scene_audio_{i}.mp3")
        image_path = os.path.join(TEMP_DIR, f"scene_bg_{i}.jpg")
        temp_files.extend([audio_path, image_path])
        
        print(f"  [장면 {i+1}] 텍스트: {text}")
        
        # A. Create background image with text using Pillow
        create_text_image(text, bg_color, image_path)
        
        # B. Create TTS audio using Edge-TTS
        await generate_tts(text, audio_path)
        
        # C. Load assets into MoviePy
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        bg_clip = ImageClip(image_path).set_duration(duration)
        video_clip = bg_clip.set_audio(audio_clip)
        
        clips.append(video_clip)
        
    # 2. Concatenate and Render Final Video
    output_filename = "auto_shorts_video.mp4"
    output_path = os.path.join(INPUT_DIR, output_filename)
    
    print(f"\n🎬 최종 숏폼 영상 렌더링 중 (저장 위치: {output_path})...")
    try:
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=4,
            logger=None
        )
        print("\n🎉 축하합니다! 영상 생성이 완전히 끝났습니다.")
        print(f"📂 결과물: {output_path}")
        print("\n다음 단계를 진행해 주세요:")
        print("  1. 'python main.py'를 실행하여 이 영상을 틱톡에 자동 업로드합니다.")
    except Exception as e:
        print(f"❌ 최종 영상 렌더링 오류: {e}")
    finally:
        # Close all clips to prevent resource lock
        for clip in clips:
            clip.close()
        try:
            final_video.close()
        except NameError:
            pass
            
        # Clean up temporary scene files
        print("🧹 임시 파일 정리 중...")
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
        print("✨ 정리 완료!")

if __name__ == "__main__":
    # If a topic was passed via command line
    user_topic = sys.argv[1] if len(sys.argv) > 1 else None
    
    asyncio.run(run_pipeline(user_topic))
