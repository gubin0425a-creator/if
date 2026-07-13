import os
import shutil

def merge():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "..", "ui", "index.html")
    mobile_path = os.path.join(base_dir, "..", "ui", "mobile.html")
    
    shutil.copyfile(index_path, mobile_path)
    
    root_index_path = os.path.join(base_dir, "..", "index.html")
    root_mobile_path = os.path.join(base_dir, "..", "mobile.html")
    shutil.copyfile(index_path, root_index_path)
    shutil.copyfile(mobile_path, root_mobile_path)
    
    print("Successfully synchronized all PC and Mobile templates to ui/ and project root!")

if __name__ == "__main__":
    merge()
