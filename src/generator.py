import os
import sys
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip

# Ensure output prints UTF-8
sys.stdout.reconfigure(encoding='utf-8')

class VideoGenerator:
    def __init__(self):
        pass
        
    def compile_video(self, video_path, output_path, tts_path=None, music_path=None, music_volume=0.15):
        """
        Compiles the final video by merging the video track with optional TTS narration and background music.
        """
        video_path = os.path.abspath(video_path)
        output_path = os.path.abspath(output_path)
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        print(f"[Generator] Loading video clip: {video_path}")
        video_clip = VideoFileClip(video_path)
        duration = video_clip.duration
        
        audio_tracks = []
        
        # 1. Load TTS Narration if provided
        tts_clip = None
        if tts_path:
            tts_path = os.path.abspath(tts_path)
            if os.path.exists(tts_path):
                print(f"[Generator] Loading TTS narration: {tts_path}")
                tts_clip = AudioFileClip(tts_path)
                # If TTS is longer than video, we can fit the video duration to TTS,
                # but for simplicity, we keep the video duration.
                audio_tracks.append(tts_clip)
            else:
                print(f"[Generator] Warning: TTS file not found at {tts_path}")
                
        # 2. Load Background Music if provided
        music_clip = None
        if music_path:
            music_path = os.path.abspath(music_path)
            if os.path.exists(music_path):
                print(f"[Generator] Loading background music: {music_path}")
                music_clip = AudioFileClip(music_path).volumex(music_volume)
                # Loop or cut music to match video duration
                if music_clip.duration > duration:
                    music_clip = music_clip.subclip(0, duration)
                else:
                    music_clip = music_clip.loop(duration=duration)
                audio_tracks.append(music_clip)
            else:
                print(f"[Generator] Warning: Music file not found at {music_path}")
                
        # 3. Handle original video audio if it exists and we aren't replacing it
        if video_clip.audio is not None and not tts_path:
            audio_tracks.insert(0, video_clip.audio)
            
        # Mix all audios
        if audio_tracks:
            print(f"[Generator] Mixing {len(audio_tracks)} audio tracks...")
            mixed_audio = CompositeAudioClip(audio_tracks)
            video_with_audio = video_clip.set_audio(mixed_audio)
        else:
            print("[Generator] No audio tracks to mix. Exporting video only.")
            video_with_audio = video_clip
            
        print(f"[Generator] Writing composite video file to: {output_path}")
        video_with_audio.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            logger=None # Suppress verbose progress logs
        )
        
        # Clean up to release file locks
        video_clip.close()
        if tts_clip:
            tts_clip.close()
        if music_clip:
            music_clip.close()
        if audio_tracks:
            video_with_audio.close()
            
        print("[Generator] Video compilation completed successfully.")
        return True
