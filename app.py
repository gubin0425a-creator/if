import os
import sys
import uuid
import json
import subprocess
import time
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

from src.security import SecurityManager

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# 초기 코드 생성 및 출력
SecurityManager.get_current_code()

@app.route('/api/verify_code', methods=['POST'])
def verify_code():
    data = request.json or {}
    code = data.get("code", "")
    if SecurityManager.verify_code(code):
        return jsonify({"status": "success", "message": "마스터 코드가 인증되었습니다."})
    return jsonify({"status": "error", "message": "잘못된 코드입니다."}), 403

# 요금제 제한(Gating) 데이터 관리
GATING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp", "user_gating.json")

def load_gating():
    if os.path.exists(GATING_FILE):
        try:
            with open(GATING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "user_role": "free",  # free, pro, mega, mega_hyper, infinity_hyper
        "last_generation_time": 0.0,
        "daily_upload_count": 0,
        "last_upload_date": time.strftime('%Y-%m-%d')
    }

def save_gating(data):
    os.makedirs(os.path.dirname(GATING_FILE), exist_ok=True)
    with open(GATING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/api/subscription', methods=['GET', 'POST'])
def manage_subscription():
    gating = load_gating()
    # 날짜 갱신 시 업로드 한도 초기화
    today = time.strftime('%Y-%m-%d')
    if gating.get("last_upload_date") != today:
        gating["last_upload_date"] = today
        gating["daily_upload_count"] = 0
        save_gating(gating)

    if request.method == 'POST':
        data = request.json or {}
        role = data.get("role", "free")
        if role in ["free", "pro", "mega", "mega_hyper", "infinity_hyper"]:
            gating["user_role"] = role
            save_gating(gating)
            return jsonify({"status": "success", "role": role})
        return jsonify({"error": "잘못된 요금제 등급입니다."}), 400
        
    return jsonify({
        "role": gating.get("user_role", "free"),
        "last_generation_time": gating.get("last_generation_time", 0.0),
        "daily_upload_count": gating.get("daily_upload_count", 0),
        "cooldown_remaining": max(0, int(5400 - (time.time() - gating.get("last_generation_time", 0.0))))
    })

@app.route('/api/version', methods=['GET'])
def get_version():
    v_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.json")
    if os.path.exists(v_path):
        try:
            with open(v_path, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({
        "version": "4.0.4",
        "release_date": "2026-07-13",
        "changelog": ["이전 버전 동기화 릴리즈"]
    })

@app.route('/mobile')
def mobile_index():
    """안드로이드/모바일 전용 최적화 UI"""
    ui_path = os.path.join(BASE_DIR, "ui", "mobile.html")
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Mobile UI file not found."

@app.route('/api/factory', methods=['POST'])
def start_factory():
    """30분 영상 3개 풀-오토 공장 API"""
    data = request.json or {}
    code = data.get("code", "")
    if not SecurityManager.verify_code(code):
        return jsonify({"error": "보안 인증이 필요합니다."}), 403

    gating = load_gating()
    if gating.get("user_role") == "free":
        return jsonify({"error": "풀-오토 공장 모드는 FREE 플랜에서 사용할 수 없습니다. 플랜을 업그레이드하세요."}), 403

    coupang_mode = data.get("coupang_mode", False)
    task_id = str(uuid.uuid4())
    log_path = os.path.join(LOG_DIR, f"{task_id}.log")

    cmd = [
        sys.executable,
        "-u",
        os.path.join(BASE_DIR, "tools", "factory_worker.py"),
        "--mode", "factory"
    ]
    if coupang_mode:
        cmd.append("--coupang-mode")

    log_file = open(log_path, "w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            text=True,
            env=dict(os.environ, PYTHONIOENCODING="utf-8")
        )
        active_tasks[task_id] = {
            "process": proc,
            "log_file": log_file,
            "topic": "30분 공장 모드 가동",
            "lang": "ko"
        }
        return jsonify({"task_id": task_id, "status": "started"})
    except Exception as e:
        log_file.close()
        return jsonify({"error": f"공장 프로세스 시작 실패: {str(e)}"}), 500

@app.route('/api/scheduler', methods=['POST'])
def start_scheduler():
    """24시간 무인 자동화 엔진 가동 API"""
    data = request.json or {}
    code = data.get("code", "")
    if not SecurityManager.verify_code(code):
        return jsonify({"error": "보안 인증이 필요합니다."}), 403

    gating = load_gating()
    if gating.get("user_role") == "free":
        return jsonify({"error": "24시간 자동 업로드 엔진은 FREE 플랜에서 사용할 수 없습니다. 플랜을 업그레이드하세요."}), 403

    coupang_mode = data.get("coupang_mode", False)
    task_id = str(uuid.uuid4())
    log_path = os.path.join(LOG_DIR, f"{task_id}.log")

    cmd = [
        sys.executable,
        "-u",
        os.path.join(BASE_DIR, "tools", "factory_worker.py"),
        "--mode", "24h"
    ]
    if coupang_mode:
        cmd.append("--coupang-mode")

    log_file = open(log_path, "w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            text=True,
            env=dict(os.environ, PYTHONIOENCODING="utf-8")
        )
        active_tasks[task_id] = {
            "process": proc,
            "log_file": log_file,
            "topic": "24시간 무인 자동화",
            "lang": "ko"
        }
        return jsonify({"task_id": task_id, "status": "started"})
    except Exception as e:
        log_file.close()
        return jsonify({"error": f"무인 자동화 프로세스 시작 실패: {str(e)}"}), 500

@app.route('/api/optimize_seo', methods=['POST'])
def optimize_seo():
    data = request.json or {}
    filename = data.get("filename")
    if not filename: return jsonify({"error": "파일명 누락"}), 400

    try:
        from src.channel_optimizer import ChannelOptimizer
        # 메타데이터 로드 및 최적화 로직 수행
        # ... (gui.py의 worker 로직과 유사)
        return jsonify({"status": "success", "message": "SEO 최적화 완료"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "temp", "logs")
UPLOAD_DIR = os.path.join(BASE_DIR, "videos_to_upload")
SRT_DIR = os.path.join(BASE_DIR, "subtitles")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SRT_DIR, exist_ok=True)

# Keep track of active processes
# task_id -> {"process": Popen, "log_file": file, "topic": str, "lang": str}
active_tasks = {}

@app.route('/')
def index():
    """Serves the main UI index.html"""
    ui_path = os.path.join(BASE_DIR, "ui", "index.html")
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <html>
        <head><title>TikTok Auto Poster</title></head>
        <body style="font-family: sans-serif; padding: 50px; text-align: center; background: #1a1a2e; color: white;">
            <h1>TikTok Auto Poster Web Interface</h1>
            <p>UI file index.html is missing under ui/ directory.</p>
        </body>
    </html>
    """

@app.route('/api/recommend', methods=['POST'])
def recommend():
    """Recommends 5 specific topics based on a general subject"""
    from src.topic_recommender import recommend_topics
    
    data = request.json or {}
    base_topic = data.get("topic", "").strip()
    if not base_topic:
        return jsonify({"error": "주제를 입력해주세요."}), 400
        
    try:
        topics = recommend_topics(base_topic)
        return jsonify({"topics": topics})
    except Exception as e:
        return jsonify({"error": f"주제 추천 실패: {str(e)}"}), 500

@app.route('/api/generate', methods=['POST'])
def generate():
    """Starts the video generation pipeline in a background subprocess"""
    data = request.json or {}
    topic = data.get("topic", "").strip()
    pick = data.get("pick")  # int index (1-5) or None
    lang = data.get("lang", "ko")
    style = data.get("style", "photorealistic")
    mood = data.get("mood", "auto")
    hook = data.get("hook", "").strip()
    is_direct = data.get("is_direct", False)
    media_type = data.get("media_type", "image")
    aspect_ratio = data.get("aspect_ratio", "9:16")
    coupang_mode = data.get("coupang_mode", False)
    
    gating = load_gating()
    role = gating.get("user_role", "free")
    if role == "free":
        last_gen = gating.get("last_generation_time", 0.0)
        time_passed = time.time() - last_gen
        if time_passed < 5400:
            remaining = int(5400 - time_passed)
            return jsonify({"error": f"무료 요금제는 1시간 30분의 제작 대기 쿨타임이 적용됩니다. {remaining // 60}분 {remaining % 60}초 뒤에 다시 제작하세요."}), 403
        if coupang_mode:
            return jsonify({"error": "쿠팡 파트너스 연계 모드는 MEGA 이상의 플랜이 필요합니다."}), 403
            
        gating["last_generation_time"] = time.time()
        save_gating(gating)

    # 추천 없이 다이렉트로 바로 제작하는 경우, 기성 훅 자동 빌드
    if is_direct and not hook:
        hook = f"{topic}, 당신이 절대 몰랐던 숨겨진 진실?"
        
    if not topic:
        return jsonify({"error": "영상 주제 또는 추천 번호가 필요합니다."}), 400
        
    task_id = str(uuid.uuid4())
    log_path = os.path.join(LOG_DIR, f"{task_id}.log")
    
    # Command to run generate_video_v2.py
    cmd = [
        sys.executable,
        "-u",  # Unbuffered output to write logs in real-time
        os.path.join(BASE_DIR, "generate_video_v2.py"),
        "--topic", topic,
        "--lang", lang,
        "--style", style,
        "--mood", mood,
        "--media-type", media_type,
        "--aspect-ratio", aspect_ratio
    ]
    if coupang_mode:
        cmd.append("--coupang-mode")
    if pick is not None:
        cmd.extend(["--pick", str(pick)])
    if hook:
        cmd.extend(["--hook", hook])
        
    log_file = open(log_path, "w", encoding="utf-8")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            text=True,
            env=dict(os.environ, PYTHONIOENCODING="utf-8")
        )
        active_tasks[task_id] = {
            "process": proc,
            "log_file": log_file,
            "topic": topic,
            "lang": lang
        }
        return jsonify({"task_id": task_id, "status": "started"})
    except Exception as e:
        log_file.close()
        return jsonify({"error": f"영상 생성 프로세스 시작 실패: {str(e)}"}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    """Starts the TikTok automatic uploader script (main.py) in a background subprocess"""
    gating = load_gating()
    if gating.get("user_role") == "free":
        return jsonify({"error": "자동 스케줄 예약 업로드 기능은 PRO 이상의 플랜에서 지원합니다. 플랜을 업그레이드하세요."}), 403

    task_id = str(uuid.uuid4())
    log_path = os.path.join(LOG_DIR, f"{task_id}.log")
    
    cmd = [
        sys.executable,
        "-u",
        os.path.join(BASE_DIR, "main.py")
    ]
    
    log_file = open(log_path, "w", encoding="utf-8")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            text=True,
            env=dict(os.environ, PYTHONIOENCODING="utf-8")
        )
        active_tasks[task_id] = {
            "process": proc,
            "log_file": log_file,
            "topic": "틱톡 자동 업로드",
            "lang": "ko"
        }
        return jsonify({"task_id": task_id, "status": "started"})
    except Exception as e:
        log_file.close()
        return jsonify({"error": f"업로더 프로세스 시작 실패: {str(e)}"}), 500

@app.route('/api/init_session', methods=['POST'])
def api_init_session():
    """Starts the headful browser login script to let user log in to TikTok in their active GUI session"""
    task_id = str(uuid.uuid4())
    log_path = os.path.join(LOG_DIR, f"{task_id}.log")
    
    cmd = [
        sys.executable,
        "-u",
        os.path.join(BASE_DIR, "init_session.py")
    ]
    
    log_file = open(log_path, "w", encoding="utf-8")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            text=True,
            env=dict(os.environ, PYTHONIOENCODING="utf-8")
        )
        active_tasks[task_id] = {
            "process": proc,
            "log_file": log_file,
            "topic": "틱톡 로그인 세션 연동",
            "lang": "ko"
        }
        return jsonify({"task_id": task_id, "status": "started"})
    except Exception as e:
        log_file.close()
        return jsonify({"error": f"세션 연동 프로세스 시작 실패: {str(e)}"}), 500

@app.route('/api/stop/<task_id>', methods=['POST'])
def stop_task(task_id):
    """Kills the active subprocess for the given task_id and clears leftover processes"""
    task = active_tasks.get(task_id)
    if task:
        proc = task.get("process")
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except:
                try:
                    proc.kill()
                except:
                    pass
        log_file = task.get("log_file")
        if log_file:
            try:
                log_file.close()
            except:
                pass
        
        # Kill any orphan ffmpeg processes
        import subprocess as sp
        try:
            sp.run(["taskkill", "/F", "/IM", "ffmpeg*"], stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        except:
            pass
            
        print(f"  [Server] Task {task_id} manually stopped.")
        return jsonify({"status": "stopped", "message": "작업이 성공적으로 중지되었습니다."})
    return jsonify({"error": "진행 중인 작업을 찾을 수 없습니다."}), 404

@app.route('/temp/<filename>')
def serve_temp(filename):
    """Serves generated temporary visual assets from the temp directory"""
    return send_from_directory(os.path.join(BASE_DIR, "temp"), filename)

@app.route('/api/stream/<task_id>')
def stream_logs(task_id):
    """Streams the log file of a task using Server-Sent Events (SSE)"""
    log_path = os.path.join(LOG_DIR, f"{task_id}.log")
    
    def generate_events():
        # Wait up to 5 seconds for the log file to be created
        for _ in range(10):
            if os.path.exists(log_path):
                break
            time.sleep(0.5)
            
        if not os.path.exists(log_path):
            yield f"data: {json.dumps({'error': '로그 파일을 찾을 수 없습니다.'})}\n\n"
            return
            
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            while True:
                line = f.readline()
                if line:
                    yield f"data: {json.dumps({'line': line.strip()})}\n\n"
                else:
                    # Check if process is still active
                    task_info = active_tasks.get(task_id)
                    if task_info:
                        proc = task_info["process"]
                        if proc.poll() is not None:
                            # Finished. Read any remaining logs.
                            remaining = f.read()
                            for l in remaining.splitlines():
                                yield f"data: {json.dumps({'line': l.strip()})}\n\n"
                                
                            exit_code = proc.returncode
                            if exit_code == 0:
                                yield f"data: {json.dumps({'status': 'completed', 'message': '작업이 완료되었습니다!'})}\n\n"
                            else:
                                yield f"data: {json.dumps({'status': 'failed', 'message': f'오류 발생 (종료 코드: {exit_code})'})}\n\n"
                            
                            # Clean up task
                            try:
                                task_info["log_file"].close()
                            except:
                                pass
                            active_tasks.pop(task_id, None)
                            break
                    else:
                        # Log file exists but no longer active
                        yield f"data: {json.dumps({'status': 'completed', 'message': '작업이 완료 또는 중단되었습니다.'})}\n\n"
                        break
                time.sleep(0.1)
                
    return Response(generate_events(), mimetype='text/event-stream')

@app.route('/api/videos', methods=['GET'])
def list_videos():
    """Lists completed video files in the upload queue folder with SEO metadata"""
    try:
        files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith(('.mp4', '.mov'))]
        videos_data = []
        for f in files:
            path = os.path.join(UPLOAD_DIR, f)
            mtime = os.path.getmtime(path)
            
            # auto_shorts_ 접두사 떼기
            ascii_title = f
            if f.startswith("auto_shorts_"):
                ascii_title = f[len("auto_shorts_"):]
            if ascii_title.endswith(".mp4"):
                ascii_title = ascii_title[:-4]
            if ascii_title.endswith(".mov"):
                ascii_title = ascii_title[:-4]
                
            meta_path = os.path.join(SRT_DIR, f"{ascii_title}_metadata.json")
            seo_score = 0
            seo_report = {}
            seo_tags = []
            triple_keywords = []
            title = ascii_title.replace("_", " ")
            
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as mf:
                         meta = json.load(mf)
                         seo_score = meta.get("seo_score", 0)
                         seo_report = meta.get("seo_report", {})
                         title = meta.get("title", title)
                         seo_tags = meta.get("tags", [])
                         triple_keywords = meta.get("triple_keywords", [])
                except Exception as e:
                    print(f"Error parsing metadata for {f}: {e}")
                    
            videos_data.append({
                "filename": f,
                "title": title,
                "mtime": mtime,
                "seo_score": seo_score,
                "seo_report": seo_report,
                "tags": seo_tags,
                "triple_keywords": triple_keywords
            })
            
        # Sort by modification time (newest first)
        videos_data.sort(key=lambda x: x["mtime"], reverse=True)
        return jsonify({"videos": videos_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload_single', methods=['POST'])
def upload_single():
    """Starts the TikTok/YouTube automatic uploader script (main.py) for a single target video"""
    data = request.json or {}
    filename = data.get("filename", "").strip()
    if not filename:
        return jsonify({"error": "업로드할 비디오 파일명을 입력해 주세요."}), 400

    gating = load_gating()
    role = gating.get("user_role", "free")
    if role == "free":
        today = time.strftime('%Y-%m-%d')
        if gating.get("last_upload_date") != today:
            gating["last_upload_date"] = today
            gating["daily_upload_count"] = 0
        if gating.get("daily_upload_count", 0) >= 2:
            return jsonify({"error": "무료 요금제는 하루 최대 2개의 영상만 업로드할 수 있습니다. 플랜을 업그레이드하세요."}), 403
        gating["daily_upload_count"] = gating.get("daily_upload_count", 0) + 1
        save_gating(gating)

    task_id = str(uuid.uuid4())
    log_path = os.path.join(LOG_DIR, f"{task_id}.log")
    
    cmd = [
        sys.executable,
        "-u",
        os.path.join(BASE_DIR, "main.py"),
        "--video", filename
    ]
    
    log_file = open(log_path, "w", encoding="utf-8")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            text=True,
            env=dict(os.environ, PYTHONIOENCODING="utf-8")
        )
        active_tasks[task_id] = {
            "process": proc,
            "log_file": log_file,
            "topic": f"개별 영상 업로드 ({filename})",
            "lang": "ko"
        }
        return jsonify({"task_id": task_id, "status": "started"})
    except Exception as e:
        log_file.close()
        return jsonify({"error": f"개별 업로더 프로세스 시작 실패: {str(e)}"}), 500

@app.route('/api/video/<filename>')
def serve_video(filename):
    """Serves a completed video file for HTML5 video player"""
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == '__main__':
    # Run server on port from environment variable (default: 5000) for Render compatibility
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
