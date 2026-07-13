import os
import shutil
from PIL import Image

def replace_launcher_icons(source_image_path, project_res_path):
    print(f"Replacing launcher icons with: {source_image_path}")
    
    # Check if source exists
    if not os.path.exists(source_image_path):
        print("Error: Source image not found!")
        return False
        
    # Open source image
    src_img = Image.open(source_image_path)
    
    # 1. Delete adaptive XML icons if present to force fallback to standard PNGs
    anydpi_path = os.path.join(project_res_path, "mipmap-anydpi-v26")
    if os.path.exists(anydpi_path):
        print("Cleaning up adaptive XML launchers...")
        shutil.rmtree(anydpi_path)
        
    # Mipmap configurations: (folder_name, size_px)
    configs = [
        ("mipmap-mdpi", 48),
        ("mipmap-hdpi", 72),
        ("mipmap-xhdpi", 96),
        ("mipmap-xxhdpi", 144),
        ("mipmap-xxxhdpi", 192)
    ]
    
    for folder, size in configs:
        target_dir = os.path.join(project_res_path, folder)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            
        # Remove any webp/png variants to avoid duplicate resource conflicts
        for file in os.listdir(target_dir):
            if file.startswith("ic_launcher"):
                os.remove(os.path.join(target_dir, file))
                
        # Resize image
        resized_img = src_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save as ic_launcher.png and ic_launcher_round.png
        png_path = os.path.join(target_dir, "ic_launcher.png")
        png_round_path = os.path.join(target_dir, "ic_launcher_round.png")
        
        resized_img.save(png_path, "PNG")
        resized_img.save(png_round_path, "PNG")
        print(f"Generated {size}x{size} icons in {folder}")
        
    print("[Success] All launcher icons updated successfully!")
    return True

if __name__ == "__main__":
    src = r"C:\Users\gubin\.gemini\antigravity\brain\207423cf-2362-49bf-a008-ebd4ad350c67\chronos_app_icon_1783858696227.png"
    res = r"c:\Users\gubin\workspace\workspace_code\chronos-app\app\src\main\res"
    replace_launcher_icons(src, res)
