import os

def test_path():
    print(f"__file__: {__file__}")
    print(f"dirname(__file__): {os.path.dirname(__file__)}")
    
    skills_dir = os.path.join(os.path.dirname(__file__), '..', '.agents', 'skills')
    print(f"skills_dir (before abspath): {skills_dir}")
    
    skills_dir = os.path.abspath(skills_dir)
    print(f"skills_dir (after abspath): {skills_dir}")
    
    print(f"exists: {os.path.exists(skills_dir)}")
    
    if os.path.exists(skills_dir):
        entries = os.listdir(skills_dir)
        print(f"entries: {entries}")
        
        for entry in entries:
            entry_path = os.path.join(skills_dir, entry)
            if os.path.isdir(entry_path):
                print(f"subdir: {entry}")
                skill_file = os.path.join(entry_path, 'SKILL.md')
                print(f"  SKILL.md exists: {os.path.exists(skill_file)}")

if __name__ == "__main__":
    test_path()
