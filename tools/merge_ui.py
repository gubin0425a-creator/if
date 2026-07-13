import os
import shutil

def merge():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "..", "ui", "index.html")
    mobile_path = os.path.join(base_dir, "..", "ui", "mobile.html")
    
    shutil.copyfile(index_path, mobile_path)
    print("Successfully synchronized ui/mobile.html with ui/index.html (100% identical)!")

if __name__ == "__main__":
    merge()
