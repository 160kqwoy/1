import os
import sys

def test_skill_load():
    skills_dir = os.path.join(os.path.dirname(__file__), '.agents', 'skills')
    skills_dir = os.path.abspath(skills_dir)
    
    print(f"技能目录路径: {skills_dir}")
    print(f"目录是否存在: {os.path.exists(skills_dir)}")
    
    if os.path.exists(skills_dir):
        entries = os.listdir(skills_dir)
        print(f"目录内容: {entries}")
        
        for entry in entries:
            entry_path = os.path.join(skills_dir, entry)
            if os.path.isdir(entry_path):
                print(f"\n子目录: {entry}")
                skill_file = os.path.join(entry_path, 'SKILL.md')
                print(f"SKILL.md路径: {skill_file}")
                print(f"SKILL.md是否存在: {os.path.exists(skill_file)}")
                
                if os.path.exists(skill_file):
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(f"文件内容:\n{content[:500]}...")

if __name__ == "__main__":
    test_skill_load()
