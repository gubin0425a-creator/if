import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
import json

# Force UTF-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")

class ChronosGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chronos v3.0 - AI Shorts Creator")
        self.root.geometry("1100x700")
        self.root.configure(bg="#1e1e2e")
        
        self.active_process = None
        self.recommended_topics = []
        
        # Configure styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background="#1e1e2e", foreground="#cdd6f4")
        self.style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Malgun Gothic", 10))
        self.style.configure("TButton", font=("Malgun Gothic", 10, "bold"), background="#89b4fa", foreground="#1e1e2e")
        self.style.map("TButton", background=[("active", "#b4befe")])
        
        # Combobox 스타일 세팅 (다크 테마 필드배경과 밝은 글자색)
        self.style.configure("TCombobox", 
                              fieldbackground="#313244", 
                              background="#313244", 
                              foreground="#cdd6f4", 
                              arrowcolor="#cdd6f4")
        self.style.map("TCombobox", 
                        fieldbackground=[("readonly", "#313244")], 
                        foreground=[("readonly", "#cdd6f4")])
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header = tk.Label(
            self.root, 
            text="Chronos v3.0 - AI Shorts Creator", 
            font=("Malgun Gothic", 18, "bold"), 
            bg="#1e1e2e", 
            fg="#cdd6f4"
        )
        header.pack(pady=15)
        
        # Main Layout Frame
        main_frame = tk.Frame(self.root, bg="#1e1e2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left Panel (Settings)
        left_panel = tk.Frame(main_frame, width=350, bg="#181825", bd=1, relief=tk.SOLID)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        tk.Label(left_panel, text="⚙️ 기획 및 설정", font=("Malgun Gothic", 12, "bold"), bg="#181825", fg="#89b4fa").pack(pady=10)
        
        # Topic Input
        tk.Label(left_panel, text="역사 주제 입력", bg="#181825", fg="#cdd6f4").pack(anchor=tk.W, padx=15, pady=(5, 0))
        self.topic_entry = tk.Entry(left_panel, bg="#313244", fg="#cdd6f4", insertbackground="white", font=("Malgun Gothic", 10))
        self.topic_entry.insert(0, "임진왜란")
        self.topic_entry.pack(fill=tk.X, padx=15, pady=5)
        
        # Language Selector
        tk.Label(left_panel, text="나레이션 & 자막 언어", bg="#181825", fg="#cdd6f4").pack(anchor=tk.W, padx=15, pady=(5, 0))
        self.lang_var = tk.StringVar(value="ko")
        lang_combo = ttk.Combobox(left_panel, textvariable=self.lang_var, values=["ko", "en", "ja"], state="readonly")
        lang_combo.pack(fill=tk.X, padx=15, pady=5)
        
        # Visual Style Selector
        tk.Label(left_panel, text="AI 이미지 비주얼 스타일", bg="#181825", fg="#cdd6f4").pack(anchor=tk.W, padx=15, pady=(5, 0))
        self.style_var = tk.StringVar(value="photorealistic")
        style_combo = ttk.Combobox(left_panel, textvariable=self.style_var, values=["photorealistic", "ink-painting", "oil-painting", "webtoon"], state="readonly")
        style_combo.pack(fill=tk.X, padx=15, pady=5)
        
        # Media Type Selector
        tk.Label(left_panel, text="비주얼 미디어 타입", bg="#181825", fg="#cdd6f4").pack(anchor=tk.W, padx=15, pady=(5, 0))
        self.media_type_var = tk.StringVar(value="image")
        media_type_combo = ttk.Combobox(left_panel, textvariable=self.media_type_var, values=["image", "video"], state="readonly")
        media_type_combo.pack(fill=tk.X, padx=15, pady=5)
        
        # Aspect Ratio Selector
        tk.Label(left_panel, text="비디오 화면 비율", bg="#181825", fg="#cdd6f4").pack(anchor=tk.W, padx=15, pady=(5, 0))
        self.aspect_ratio_var = tk.StringVar(value="9:16")
        aspect_ratio_combo = ttk.Combobox(left_panel, textvariable=self.aspect_ratio_var, values=["9:16", "16:9"], state="readonly")
        aspect_ratio_combo.pack(fill=tk.X, padx=15, pady=5)
        
        # Mood Selector
        tk.Label(left_panel, text="배경음악 분위기 스타일", bg="#181825", fg="#cdd6f4").pack(anchor=tk.W, padx=15, pady=(5, 0))
        self.mood_var = tk.StringVar(value="auto")
        mood_combo = ttk.Combobox(left_panel, textvariable=self.mood_var, values=["auto", "epic", "mystery", "sad", "tension", "neutral"], state="readonly")
        mood_combo.pack(fill=tk.X, padx=15, pady=5)
        
        # Action Buttons
        self.recommend_btn = tk.Button(left_panel, text="🪄 AI 소주제 추천받기", bg="#f9e2af", fg="#1e1e2e", font=("Malgun Gothic", 10, "bold"), command=self.start_recommend)
        self.recommend_btn.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        self.direct_btn = tk.Button(left_panel, text="⚡ 추천 없이 바로 제작", bg="#fab387", fg="#1e1e2e", font=("Malgun Gothic", 10, "bold"), command=self.start_direct_gen)
        self.direct_btn.pack(fill=tk.X, padx=15, pady=5)
        
        self.session_btn = tk.Button(left_panel, text="🔑 틱톡 로그인 세션 연동", bg="#89dceb", fg="#1e1e2e", font=("Malgun Gothic", 10, "bold"), command=self.start_session_link)
        self.session_btn.pack(fill=tk.X, padx=15, pady=5)
        
        self.upload_btn = tk.Button(left_panel, text="📲 틱톡 & 유튜브 자동 업로드", bg="#a6e3a1", fg="#1e1e2e", font=("Malgun Gothic", 10, "bold"), command=self.start_upload)
        self.upload_btn.pack(fill=tk.X, padx=15, pady=5)
        
        self.stop_btn = tk.Button(left_panel, text="🛑 모든 작업 중지", bg="#f38ba8", fg="#1e1e2e", font=("Malgun Gothic", 10, "bold"), command=self.stop_active_process, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        # Right Panel (Console & Suggestions)
        right_panel = tk.Frame(main_frame, bg="#1e1e2e")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Upper Right: Recommendation Cards Area
        self.cards_frame = tk.LabelFrame(right_panel, text="📺 소주제 추천 카드 (클릭 시 제작 시작)", bg="#1e1e2e", fg="#89b4fa", font=("Malgun Gothic", 10, "bold"), height=240)
        self.cards_frame.pack(fill=tk.X, pady=(0, 10))
        self.cards_frame.pack_propagate(False)
        
        self.placeholder_label = tk.Label(self.cards_frame, text="주제를 입력하고 'AI 소주제 추천받기' 버튼을 누르시면 여기에 추천 카드가 표시됩니다.", bg="#1e1e2e", fg="#a6adc8")
        self.placeholder_label.pack(expand=True)
        
        # Lower Right: Console logs
        console_frame = tk.LabelFrame(right_panel, text="⚙️ 실시간 렌더링 및 프로그램 실행 로그", bg="#1e1e2e", fg="#a6e3a1", font=("Malgun Gothic", 10, "bold"))
        console_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.log_text = scrolledtext.ScrolledText(console_frame, bg="#11111b", fg="#a6e3a1", font=("Consolas", 10), insertbackground="white")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.insert(tk.END, "📢 Chronos 데스크탑 프로그램이 준비되었습니다.\n원하는 세팅 완료 후 실행해 주세요.\n")
        
        # Bottom Right: Completed Videos Library
        library_frame = tk.LabelFrame(right_panel, text="🎬 제작 완료 영상 보관함 (Library)", bg="#1e1e2e", fg="#fab387", font=("Malgun Gothic", 10, "bold"), height=180)
        library_frame.pack(fill=tk.X)
        library_frame.pack_propagate(False)
        
        # Scrollbar for treeview
        tree_scroll = tk.Scrollbar(library_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.library_tree = ttk.Treeview(
            library_frame, 
            columns=("name", "seo", "size", "time"), 
            show="headings", 
            yscrollcommand=tree_scroll.set, 
            height=6
        )
        tree_scroll.config(command=self.library_tree.yview)
        
        # Configure treeview headers
        self.library_tree.heading("name", text="파일명", anchor=tk.W)
        self.library_tree.heading("seo", text="SEO 점수", anchor=tk.CENTER)
        self.library_tree.heading("size", text="크기 (MB)", anchor=tk.CENTER)
        self.library_tree.heading("time", text="생성 일시", anchor=tk.CENTER)
        
        # Configure treeview column widths
        self.library_tree.column("name", width=330, anchor=tk.W)
        self.library_tree.column("seo", width=80, anchor=tk.CENTER)
        self.library_tree.column("size", width=80, anchor=tk.CENTER)
        self.library_tree.column("time", width=140, anchor=tk.CENTER)
        
        self.library_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons frame (on the right of Treeview, inside Library Frame)
        btn_frame = tk.Frame(library_frame, bg="#1e1e2e")
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        self.play_btn = tk.Button(btn_frame, text="▶️ 영상 재생", bg="#a6e3a1", fg="#1e1e2e", font=("Malgun Gothic", 9, "bold"), width=15, command=self.play_selected_video)
        self.play_btn.pack(pady=3)
        
        self.folder_btn = tk.Button(btn_frame, text="📂 폴더 열기", bg="#89dceb", fg="#1e1e2e", font=("Malgun Gothic", 9, "bold"), width=15, command=self.open_video_folder)
        self.folder_btn.pack(pady=3)
        
        self.refresh_btn = tk.Button(btn_frame, text="🔄 새로고침", bg="#cdd6f4", fg="#1e1e2e", font=("Malgun Gothic", 9, "bold"), width=15, command=self.refresh_library)
        self.refresh_btn.pack(pady=3)
        
        # Initial scan of library
        self.refresh_library()
        
    def log(self, message):
        # Strip or replace characters > U+FFFF (BMP limit) to prevent Tkinter crashes
        clean_msg = "".join([c if ord(c) <= 0xffff else "[Emoji]" for c in message])
        try:
            self.log_text.insert(tk.END, clean_msg)
            self.log_text.see(tk.END)
        except Exception:
            pass
        
    def set_buttons_state(self, state):
        self.recommend_btn.configure(state=state)
        self.direct_btn.configure(state=state)
        self.session_btn.configure(state=state)
        self.upload_btn.configure(state=state)
        if state == tk.NORMAL:
            self.stop_btn.configure(state=tk.DISABLED)
        else:
            self.stop_btn.configure(state=tk.NORMAL)
            
    def stop_active_process(self):
        if self.active_process:
            self.log("\n[System] 🛑 사용자가 작업을 강제 중지했습니다.\n")
            try:
                self.active_process.terminate()
                self.active_process.wait(timeout=1)
            except:
                try:
                    self.active_process.kill()
                except:
                    pass
            self.active_process = None
            self.set_buttons_state(tk.NORMAL)
            
            # Kill orphan processes (ffmpeg, etc.)
            try:
                subprocess.run(["taskkill", "/F", "/IM", "ffmpeg*"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
                
    def run_cmd_in_thread(self, cmd, on_finish=None):
        def worker():
            self.set_buttons_state(tk.DISABLED)
            try:
                self.active_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=BASE_DIR,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=dict(os.environ, PYTHONIOENCODING="utf-8")
                )
                
                # Stream logs in real-time
                while True:
                    line = self.active_process.stdout.readline()
                    if not line and self.active_process.poll() is not None:
                        break
                    if line:
                        self.root.after(0, self.log, line)
                        
                rc = self.active_process.returncode
                if rc == 0:
                    self.root.after(0, self.log, "\n[System] ✅ 작업이 성공적으로 완료되었습니다!\n")
                else:
                    self.root.after(0, self.log, f"\n[System] ❌ 작업 종료 (종료 코드: {rc})\n")
            except Exception as e:
                self.root.after(0, self.log, f"\n[System] 오류 발생: {str(e)}\n")
            finally:
                self.active_process = None
                self.root.after(0, self.set_buttons_state, tk.NORMAL)
                self.root.after(0, self.refresh_library)
                if on_finish:
                    self.root.after(0, on_finish)
                    
        threading.Thread(target=worker, daemon=True).start()

    def start_recommend(self):
        topic = self.topic_entry.get().strip()
        if not topic:
            messagebox.showwarning("경고", "주제를 입력해 주세요.")
            return
            
        self.log(f"\n[System] 🪄 '{topic}' 주제로 AI 소주제 추천을 로딩 중...\n")
        self.placeholder_label.pack_forget()
        for child in self.cards_frame.winfo_children():
            if child != self.placeholder_label:
                child.destroy()
                
        loading_label = tk.Label(self.cards_frame, text="⏳ Gemini AI가 평행세계 소주제를 기획하는 중...", bg="#1e1e2e", fg="#fab387", font=("Malgun Gothic", 10, "bold"))
        loading_label.pack(expand=True)
        
        def run_recommendation():
            try:
                # import recommendation function dynamically to avoid load delay
                from src.topic_recommender import recommend_topics
                topics = recommend_topics(topic)
                
                def render():
                    loading_label.destroy()
                    self.recommended_topics = topics
                    
                    # Create horizontal layout for cards
                    cards_container = tk.Frame(self.cards_frame, bg="#1e1e2e")
                    cards_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                    
                    for t in topics:
                        card_btn = tk.Button(
                            cards_container,
                            text=f"【 INDEX {t['index']} 】\n\n{t['title']}\n\n💡 {t['hook']}",
                            bg="#313244",
                            fg="#cdd6f4",
                            font=("Malgun Gothic", 9, "bold"),
                            bd=1,
                            relief=tk.RAISED,
                            cursor="hand2",
                            wraplength=140,
                            justify=tk.CENTER,
                            activebackground="#45475a",
                            activeforeground="#f9e2af",
                            command=lambda title=t['title'], hook=t['hook'], idx=t['index']: self.start_card_generation(title, hook, idx)
                        )
                        card_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
                    self.log(f"[System] ✅ 소주제 추천 완료 (5개 카드 로드됨)\n")
                    
                self.root.after(0, render)
            except Exception as e:
                def render_err():
                    loading_label.destroy()
                    self.placeholder_label.pack(expand=True)
                    self.log(f"[System] ❌ 추천 실패: {str(e)}\n")
                    messagebox.showerror("오류", f"추천 실패: {str(e)}")
                self.root.after(0, render_err)
                
        threading.Thread(target=run_recommendation, daemon=True).start()

    def start_card_generation(self, title, hook, index):
        if not messagebox.askyesno("확인", f"선택하신 '{title}' 주제로 동영상 제작을 시작하시겠습니까?"):
            return
        
        self.topic_entry.delete(0, tk.END)
        self.topic_entry.insert(0, title)
        
        cmd = [
            os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe"),
            "-u",
            os.path.join(BASE_DIR, "generate_video_v2.py"),
            "--topic", title,
            "--hook", hook,
            "--lang", self.lang_var.get(),
            "--style", self.style_var.get(),
            "--mood", self.mood_var.get(),
            "--media-type", self.media_type_var.get(),
            "--aspect-ratio", self.aspect_ratio_var.get()
        ]
        self.log(f"\n[System] 🚀 선택된 카드 주제로 영상 빌드를 실행합니다...\n")
        self.run_cmd_in_thread(cmd)

    def start_direct_gen(self):
        topic = self.topic_entry.get().strip()
        if not topic:
            messagebox.showwarning("경고", "주제를 입력해 주세요.")
            return
            
        if not messagebox.askyesno("확인", f"'{topic}' 주제로 소주제 추천 없이 바로 영상을 제작하시겠습니까?"):
            return
            
        default_hook = f"{topic}, 당신이 절대 몰랐던 숨겨진 진실?"
        cmd = [
            os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe"),
            "-u",
            os.path.join(BASE_DIR, "generate_video_v2.py"),
            "--topic", topic,
            "--hook", default_hook,
            "--lang", self.lang_var.get(),
            "--style", self.style_var.get(),
            "--mood", self.mood_var.get(),
            "--media-type", self.media_type_var.get(),
            "--aspect-ratio", self.aspect_ratio_var.get()
        ]
        self.log(f"\n[System] 🚀 추천 없는 대주제 즉시 영상 빌드를 가동합니다...\n")
        self.run_cmd_in_thread(cmd)

    def start_session_link(self):
        # Check if uploader is currently active to avoid ProcessSingleton Chrome lock
        if self.active_process:
            messagebox.showerror("오류", "현재 다른 작업이 실행 중입니다. 중지하거나 대기한 후 실행해 주세요.")
            return
            
        if not messagebox.askyesno("확인", "틱톡 로그인 세션 연동을 가동하시겠습니까?\n\n구글 크롬 브라우저가 화면에 팝업되면, 로그인을 완료하신 뒤 크롬 창을 닫아주시면 세션이 자동 저장됩니다."):
            return
            
        cmd = [
            os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe"),
            "-u",
            os.path.join(BASE_DIR, "init_session.py")
        ]
        self.log(f"\n[System] 🔑 틱톡 로그인 세션 연동 브라우저 실행 중...\n")
        self.run_cmd_in_thread(cmd)

    def start_upload(self):
        if self.active_process:
            messagebox.showerror("오류", "현재 다른 작업이 실행 중입니다. 중지하거나 대기한 후 실행해 주세요.")
            return
            
        selected = self.library_tree.selection()
        cmd = [
            os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe"),
            "-u",
            os.path.join(BASE_DIR, "main.py")
        ]
        
        if selected:
            item = self.library_tree.item(selected[0])
            filename = item["values"][0]
            cmd.extend(["--video", filename])
            self.log(f"\n[System] 📲 선택된 개별 영상 업로드 시작 ({filename})...\n")
        else:
            self.log(f"\n[System] 📲 대기열 모든 영상 일괄 자동 업로드 시작...\n")
            
        self.run_cmd_in_thread(cmd)

    def refresh_library(self):
        """videos_to_upload 폴더를 스캔하여 영상 리스트를 갱신합니다."""
        for item in self.library_tree.get_children():
            self.library_tree.delete(item)
            
        UPLOAD_DIR = os.path.join(BASE_DIR, "videos_to_upload")
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            
        try:
            files = []
            for f in os.listdir(UPLOAD_DIR):
                if f.endswith(".mp4"):
                    fp = os.path.join(UPLOAD_DIR, f)
                    stat = os.stat(fp)
                    size_mb = f"{stat.st_size / (1024 * 1024):.2f}"
                    mtime = stat.st_mtime
                    import datetime
                    dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    
                    # auto_shorts_ 접두사 제거해서 메타데이터 JSON 찾기
                    ascii_title = f
                    if f.startswith("auto_shorts_"):
                        ascii_title = f[len("auto_shorts_"):]
                    if ascii_title.endswith(".mp4"):
                        ascii_title = ascii_title[:-4]
                        
                    meta_path = os.path.join(BASE_DIR, "subtitles", f"{ascii_title}_metadata.json")
                    seo_score = "0점"
                    
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, "r", encoding="utf-8") as mf:
                                meta = json.load(mf)
                                seo_score = f"{meta.get('seo_score', 0)}점"
                        except:
                            pass
                            
                    files.append((f, seo_score, size_mb, dt, mtime))
            
            files_sorted = sorted(files, key=lambda x: x[4], reverse=True)
            for f, seo, sz, dt, _ in files_sorted:
                self.library_tree.insert("", tk.END, values=(f, seo, sz, dt))
        except Exception as e:
            self.log(f"[System] ⚠️ 보관함 스캔 실패: {e}\n")

    def play_selected_video(self):
        """선택된 영상을 OS 기본 플레이어로 재생합니다."""
        selected = self.library_tree.selection()
        if not selected:
            messagebox.showwarning("알림", "재생할 동영상을 목록에서 선택해 주세요.")
            return
        
        item = self.library_tree.item(selected[0])
        filename = item["values"][0]
        filepath = os.path.join(BASE_DIR, "videos_to_upload", filename)
        
        if os.path.exists(filepath):
            try:
                os.startfile(filepath)
            except Exception as e:
                messagebox.showerror("오류", f"재생 실패: {e}")
        else:
            messagebox.showerror("오류", "해당 파일이 존재하지 않습니다.")

    def open_video_folder(self):
        """영상 저장 폴더를 탐색기로 엽니다."""
        UPLOAD_DIR = os.path.join(BASE_DIR, "videos_to_upload")
        if os.path.exists(UPLOAD_DIR):
            try:
                os.startfile(UPLOAD_DIR)
            except Exception as e:
                messagebox.showerror("오류", f"폴더 열기 실패: {e}")
        else:
            messagebox.showerror("오류", "폴더가 존재하지 않습니다.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChronosGUI(root)
    root.mainloop()
