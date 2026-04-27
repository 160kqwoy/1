import os

def list_available_skills():
    skills_dir = os.path.join(os.path.dirname(__file__), '..', '.agents', 'skills')
    skills_dir = os.path.abspath(skills_dir)
    skills = []
    
    print(f"技能目录路径: {skills_dir}")
    
    if not os.path.exists(skills_dir):
        print(f"技能目录不存在")
        return skills
    
    print(f"技能目录存在，正在扫描...")
    
    try:
        entries = os.listdir(skills_dir)
        print(f"目录条目: {entries}")
        
        for entry in entries:
            entry_path = os.path.join(skills_dir, entry)
            if os.path.isdir(entry_path):
                print(f"发现子目录: {entry}")
                skill_file = os.path.join(entry_path, 'SKILL.md')
                print(f"技能文件路径: {skill_file}")
                
                if os.path.exists(skill_file):
                    print(f"技能文件存在")
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    print(f"文件内容前200字符: {content[:200]}")
                    
                    yaml_start = content.find('---')
                    yaml_end = content.find('---', yaml_start + 3)
                    
                    print(f"yaml_start: {yaml_start}, yaml_end: {yaml_end}")
                    
                    if yaml_start != -1 and yaml_end != -1:
                        yaml_content = content[yaml_start + 3:yaml_end].strip()
                        print(f"YAML内容: {yaml_content}")
                        
                        name = ''
                        description = ''
                        
                        for line in yaml_content.split('\n'):
                            line = line.strip()
                            print(f"YAML行: {repr(line)}")
                            if line.startswith('name:'):
                                name = line[5:].strip().strip('"').strip("'")
                                print(f"提取name: {name}")
                            elif line.startswith('description:'):
                                description = line[12:].strip().strip('"').strip("'")
                                print(f"提取description: {description}")
                        
                        if name:
                            skills.append({
                                'name': name,
                                'description': description if description else '无描述'
                            })
                            print(f"加载技能成功: {name}")
                        else:
                            print("技能文件缺少name字段")
                    else:
                        print("技能文件缺少YAML front matter")
                else:
                    print("技能文件不存在")
    
    except Exception as e:
        print(f"发生错误: {str(e)}")
    
    print(f"共加载 {len(skills)} 个技能")
    return skills

if __name__ == "__main__":
    skills = list_available_skills()
    print(f"最终技能列表: {skills}")
