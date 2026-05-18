import http.client
import json
import os
import time
import re
import subprocess
import shlex
from urllib.parse import urlparse, quote
from datetime import datetime
from typing import List, Dict, Any, Optional

# 导入长期记忆管理器
try:
    from memory_manager import get_memory_manager
    memory_manager = get_memory_manager()
    MEMORY_ENABLED = True
except ImportError:
    MEMORY_ENABLED = False
    print("[警告] 无法导入记忆管理器，记忆功能已禁用")

class ChainedCallContext:
    """链式调用上下文管理器，用于在多个工具调用之间传递数据和状态"""
    
    def __init__(self, max_iterations: int = 5, max_context_chars: int = 8000):
        """
        初始化链式调用上下文
        
        Args:
            max_iterations: 最大迭代次数，防止无限循环，默认5次
            max_context_chars: 最大上下文字符数，超过时进行压缩，默认8000字符
        """
        self.max_iterations = max_iterations
        self.max_context_chars = max_context_chars
        self.iteration_count = 0
        self.call_history: List[Dict[str, Any]] = []
        self.memory: Dict[str, Any] = {}
        self.is_complete = False
        self.final_result = None
        self.compress_count = 0  # 压缩次数记录
    
    def start_call(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """记录工具调用开始"""
        if self.iteration_count >= self.max_iterations:
            raise StopIteration(f"已达到最大迭代次数 {self.max_iterations}")
        
        self.iteration_count += 1
        call_record = {
            'iteration': self.iteration_count,
            'tool_name': tool_name,
            'arguments': arguments,
            'start_time': datetime.now().isoformat(),
            'status': 'running',
            'result': None,
            'end_time': None
        }
        self.call_history.append(call_record)
    
    def end_call(self, tool_name: str, result: Any) -> None:
        """记录工具调用结束"""
        for call in reversed(self.call_history):
            if call['tool_name'] == tool_name and call['status'] == 'running':
                call['result'] = result
                call['end_time'] = datetime.now().isoformat()
                call['status'] = 'completed'
                break
    
    def store_variable(self, name: str, value: Any) -> None:
        """存储中间变量供后续步骤使用"""
        self.memory[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取存储的中间变量"""
        return self.memory.get(name, default)
    
    def get_last_result(self) -> Any:
        """获取上一次工具调用的结果"""
        for call in reversed(self.call_history):
            if call['status'] == 'completed':
                return call['result']
        return None
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """获取完整的调用历史"""
        return self.call_history
    
    def get_iteration_count(self) -> int:
        """获取当前迭代次数"""
        return self.iteration_count
    
    def has_more_iterations(self) -> bool:
        """检查是否还有剩余迭代次数"""
        return self.iteration_count < self.max_iterations
    
    def set_complete(self, final_result: Any = None) -> None:
        """标记链式调用完成"""
        self.is_complete = True
        self.final_result = final_result
    
    def is_chained_call_complete(self) -> bool:
        """检查链式调用是否已完成"""
        return self.is_complete or self.iteration_count >= self.max_iterations
    
    def get_summary(self) -> str:
        """生成链式调用摘要"""
        summary = f"链式调用摘要:\n"
        summary += f"总迭代次数: {self.iteration_count}/{self.max_iterations}\n"
        summary += f"完成状态: {'已完成' if self.is_complete else '进行中'}\n"
        summary += "="*50 + "\n"
        
        for call in self.call_history:
            status_icon = "✅" if call['status'] == 'completed' else "🔄"
            summary += f"{status_icon} 第{call['iteration']}次调用: {call['tool_name']}\n"
            summary += f"   参数: {json.dumps(call['arguments'], ensure_ascii=False)}\n"
            if call['result']:
                result_str = str(call['result'])
                if len(result_str) > 100:
                    result_str = result_str[:100] + "..."
                summary += f"   结果: {result_str}\n"
        
        if self.memory:
            summary += "="*50 + "\n"
            summary += "存储的变量:\n"
            for key, value in self.memory.items():
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:50] + "..."
                summary += f"   {key}: {value_str}\n"
        
        return summary
    
    def get_context_length(self) -> int:
        """计算当前上下文的总字符长度"""
        total_length = 0
        for call in self.call_history:
            total_length += len(json.dumps(call, ensure_ascii=False))
        for value in self.memory.values():
            total_length += len(str(value))
        return total_length
    
    def compress_context(self, keep_recent: int = 2) -> None:
        """
        压缩上下文，保留最近的几次调用记录
        
        Args:
            keep_recent: 保留最近的调用次数，默认保留2次
        """
        if len(self.call_history) <= keep_recent:
            return
        
        # 压缩历史记录，只保留最近的
        old_calls = self.call_history[:-keep_recent]
        self.call_history = self.call_history[-keep_recent:]
        
        # 创建压缩摘要
        compression_summary = f"[已压缩] 前{len(old_calls)}次工具调用已合并"
        self.store_variable(f"compressed_{self.compress_count}", compression_summary)
        self.compress_count += 1
        
        print(f"[上下文压缩] 已压缩{len(old_calls)}条历史记录，保留最近{keep_recent}条")
    
    def clear_memory(self, keep_keys: list = None) -> None:
        """
        清理记忆中的变量
        
        Args:
            keep_keys: 需要保留的变量名列表
        """
        if keep_keys is None:
            keep_keys = []
        
        keys_to_remove = [key for key in self.memory if key not in keep_keys]
        for key in keys_to_remove:
            del self.memory[key]
        
        print(f"[记忆清理] 已清理{len(keys_to_remove)}个变量，保留{len(keep_keys)}个变量")
    
    def merge_memory(self, other_memory: dict) -> None:
        """
        合并外部记忆到当前上下文
        
        Args:
            other_memory: 外部记忆字典
        """
        self.memory.update(other_memory)
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        if not self.memory:
            return "无存储的变量"
        
        summary = "存储的变量:\n"
        for key, value in self.memory.items():
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:50] + "..."
            summary += f"  - {key}: {value_str}\n"
        return summary

def load_env():
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
    else:
        env_vars['LLM_BASE_URL'] = 'http://localhost:1234/v1'
        env_vars['LLM_MODEL'] = 'gpt-4o-mini'
    
    if 'ANYTHINGLLM_API_KEY' not in env_vars:
        env_vars['ANYTHINGLLM_API_KEY'] = ''
    
    return env_vars

def list_available_skills():
    """读取技能列表，从.agents/skills目录下的子目录读取SKILL.md文件"""
    skills_dir = os.path.join(os.path.dirname(__file__), '..', '.agents', 'skills')
    skills_dir = os.path.abspath(skills_dir)
    skills = []
    
    if not os.path.exists(skills_dir):
        return skills
    
    try:
        entries = os.listdir(skills_dir)
        for entry in entries:
            entry_path = os.path.join(skills_dir, entry)
            if os.path.isdir(entry_path):
                skill_file = os.path.join(entry_path, 'SKILL.md')
                if os.path.exists(skill_file):
                    try:
                        with open(skill_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        yaml_start = content.find('---')
                        yaml_end = content.find('---', yaml_start + 3)
                        
                        if yaml_start != -1 and yaml_end != -1:
                            yaml_content = content[yaml_start + 3:yaml_end].strip()
                            
                            name = ''
                            description = ''
                            
                            for line in yaml_content.split('\n'):
                                line = line.strip()
                                if line.startswith('name:'):
                                    name = line[5:].strip().strip('"').strip("'")
                                elif line.startswith('description:'):
                                    description = line[12:].strip().strip('"').strip("'")
                            
                            if name:
                                skills.append({
                                    'name': name,
                                    'description': description if description else '无描述'
                                })
                    except Exception as e:
                        pass
        print(f"[系统] 共加载 {len(skills)} 个技能")
    except Exception as e:
        print(f"[系统] 读取技能目录失败: {str(e)}")
    
    return skills

def load_skill_content(skill_name):
    """加载指定技能的正文内容（YAML front matter之后的部分）"""
    skills_dir = os.path.join(os.path.dirname(__file__), '..', '.agents', 'skills')
    skills_dir = os.path.abspath(skills_dir)
    
    try:
        entries = os.listdir(skills_dir)
        for entry in entries:
            entry_path = os.path.join(skills_dir, entry)
            if os.path.isdir(entry_path):
                skill_file = os.path.join(entry_path, 'SKILL.md')
                if os.path.exists(skill_file):
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    yaml_start = content.find('---')
                    yaml_end = content.find('---', yaml_start + 3)
                    
                    if yaml_start != -1 and yaml_end != -1:
                        yaml_content = content[yaml_start + 3:yaml_end].strip()
                        
                        name = ''
                        for line in yaml_content.split('\n'):
                            line = line.strip()
                            if line.startswith('name:'):
                                name = line[5:].strip().strip('"').strip("'")
                                break
                        
                        if name == skill_name:
                            body_content = content[yaml_end + 3:].strip()
                            return body_content
        
        return f"未找到技能: {skill_name}"
    except Exception as e:
        return f"加载技能失败: {str(e)}"

def get_system_prompt(skills=None):
    if skills is None:
        skills = list_available_skills()
    
    tools = [
        {
            "name": "search_history",
            "description": "搜索聊天历史记录，当用户使用/search开头或表达'查找聊天历史'意思时调用",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                    "required": True
                }
            }
        },
        {
            "name": "anythingllm_query",
            "description": "向AnythingLLM查询数据，当用户需要查询知识库中的信息时调用",
            "parameters": {
                "message": {
                    "type": "string",
                    "description": "要查询的问题或内容",
                    "required": True
                }
            }
        },
        {
            "name": "read_file",
            "description": "读取指定文件的内容",
            "parameters": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径",
                    "required": True
                }
            }
        },
        {
            "name": "write_file",
            "description": "将内容写入指定文件，支持追加模式",
            "parameters": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径",
                    "required": True
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容",
                    "required": True
                },
                "append": {
                    "type": "boolean",
                    "description": "是否追加模式，默认False（覆盖）",
                    "required": False
                }
            }
        },
        {
            "name": "delete_file",
            "description": "删除指定文件",
            "parameters": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径",
                    "required": True
                }
            }
        },
        {
            "name": "list_files",
            "description": "列出指定目录中的文件和子目录",
            "parameters": {
                "directory": {
                    "type": "string",
                    "description": "目录路径",
                    "required": True
                }
            }
        },
        {
            "name": "use_skill",
            "description": "使用指定的技能，当用户的请求需要使用某个技能时调用",
            "parameters": {
                "skill_name": {
                    "type": "string",
                    "description": "技能名称",
                    "required": True
                }
            }
        },
        {
            "name": "curl_url",
            "description": "访问指定URL并获取网页内容，当用户需要访问网页获取信息时调用",
            "parameters": {
                "url": {
                    "type": "string",
                    "description": "要访问的URL地址",
                    "required": True
                }
            }
        }
    ]
    
    skills_json = json.dumps({"skills": skills}, ensure_ascii=False, indent=2)
    
    system_prompt = f"""你是一个具有高级推理能力的聊天助手，支持链式工具调用（Chained Tool Calls）。

## 可用技能列表
{skills_json}

## 可用工具
{json.dumps(tools, ensure_ascii=False, indent=2)}

## 工具调用格式
<function_calls>
{{
    "name": "工具名称",
    "arguments": {{
        "参数名": "参数值"
    }}
}}
</function_calls>

## 链式工具调用规则

### 1. 顺序依赖关系
- 工具调用可以形成链式序列，前一个工具的输出可以作为后一个工具的输入
- 复杂任务可能需要多轮工具调用才能完成
- 工具调用顺序应符合逻辑流程（例如：先列出目录，再读取文件）

### 2. 中间结果处理
- 每轮工具调用后，结果会自动保存到上下文变量中
- 上下文变量命名格式: result_1, result_2, result_3...
- 你可以引用这些变量作为后续工具调用的参数
- 例如：先用 list_files 获取文件名，再用 read_file 读取该文件

### 3. 决策指导
- 分析当前已获取的信息是否足够回答用户问题
- 如果信息不足，选择合适的工具继续获取信息
- 如果信息充足，直接给出最终回答
- 每轮调用后检查是否达到目标

### 4. 上下文变量使用方式
- 使用 {{result_N}} 格式引用第N轮的工具执行结果
- 例如：{{result_1}} 表示第一轮工具调用的结果
- 可以从结果中提取特定值作为后续工具的参数

### 5. 链式调用示例

场景：用户需要列出目录内容，然后读取其中的README.md文件

第一轮调用:
<function_calls>
{{
    "name": "list_files",
    "arguments": {{
        "directory": "."
    }}
}}
</function_calls>

工具执行结果:
目录内容 (.):
[DIR]  practice01
[FILE] README.md (4520 bytes)

第二轮调用（基于第一轮结果）:
<function_calls>
{{
    "name": "read_file",
    "arguments": {{
        "file_path": "README.md"
    }}
}}
</function_calls>

工具执行结果:
文件内容:
# AI智能体开发教学项目
...

第三轮（信息足够，直接回答）:
已完成以下操作：
1. 列出了目录内容，发现README.md文件
2. 读取了README.md文件内容

文件内容摘要：该项目包含practice01-practice08等练习模块...

### 6. 工具选择指南
- 搜索历史: search_history(query) - 查找聊天历史记录
- 查询知识库: anythingllm_query(message) - 向知识库提问
- 读取文件: read_file(file_path) - 获取文件内容
- 写入文件: write_file(file_path, content, append) - 保存内容到文件
- 删除文件: delete_file(file_path) - 删除指定文件
- 列出目录: list_files(directory) - 查看目录结构
- 使用技能: use_skill(skill_name) - 调用特定技能
- 访问网页: curl_url(url) - 访问指定URL获取网页内容

### 7. 格式要求
- 调用工具时必须使用<function_calls>标签包裹
- 参数必须是有效的JSON格式
- 不需要调用工具时，直接用自然语言回答

支持最多{5}轮工具调用，请高效规划调用步骤。"""
    
    return system_prompt

def llm_request(env_vars, messages, stream=True):
    parsed_url = urlparse(env_vars['LLM_BASE_URL'])
    host = parsed_url.hostname or parsed_url.netloc
    port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
    path = parsed_url.path or '/v1/chat/completions'
    
    if not path.endswith('/chat/completions'):
        if path.endswith('/'):
            path = path + 'chat/completions'
        else:
            path = path + '/chat/completions'
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {env_vars.get('LLM_API_KEY', 'sk-xxx')}"
    }
    
    data = {
        'model': env_vars['LLM_MODEL'],
        'messages': messages,
        'stream': stream,
        'max_tokens': 8192,
        'temperature': 0.7
    }
    
    try:
        if parsed_url.scheme == 'https':
            conn = http.client.HTTPSConnection(host, port, timeout=120)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=120)
        
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        print(f"[系统] 发送请求: {host}:{port}{path}")
        print(f"[系统] 请求体大小: {len(body)} 字节")
        conn.request('POST', path, body=body, headers=headers)
        response = conn.getresponse()
        print(f"[系统] 响应状态码: {response.status}")
        
        if response.status == 200:
            if stream:
                # 流式输出处理
                print("[系统] 开始流式接收响应...")
                content = ""
                buffer = ""
                
                while True:
                    chunk = response.read(1024)
                    if not chunk:
                        break
                    
                    buffer += chunk.decode('utf-8')
                    
                    # 处理 SSE 格式的流式响应
                    while 'data: ' in buffer:
                        data_start = buffer.find('data: ')
                        # 查找换行符或结束标记
                        line_end = buffer.find('\n', data_start)
                        if line_end == -1:
                            break
                        
                        line = buffer[data_start + 6:line_end].strip()
                        buffer = buffer[line_end + 1:]
                        
                        if line == '[DONE]':
                            break
                        
                        if line:
                            try:
                                obj = json.loads(line)
                                if obj.get('choices') and len(obj['choices']) > 0:
                                    delta = obj['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        token = delta['content']
                                        content += token
                                        # 实时输出token
                                        print(token, end='', flush=True)
                            except json.JSONDecodeError:
                                continue
                
                print("\n")
                return content, None
            else:
                # 非流式输出处理
                response_data = response.read().decode('utf-8')
                print(f"[系统] 响应体大小: {len(response_data)} 字节")
                
                try:
                    obj = json.loads(response_data)
                    
                    if 'error' in obj:
                        print(f"\n[LLM错误] {obj['error']}")
                        return None, None
                    
                    if obj.get('choices') and len(obj['choices']) > 0:
                        content = obj['choices'][0].get('message', {}).get('content', '')
                        usage = obj.get('usage', {})
                        
                        if not content:
                            print(f"\n[LLM错误] 响应内容为空")
                            return None, None
                        
                        return content, {
                            'prompt_tokens': usage.get('prompt_tokens', 0),
                            'completion_tokens': usage.get('completion_tokens', 0),
                            'total_tokens': usage.get('total_tokens', 0)
                        }
                    else:
                        print(f"\n[LLM错误] 没有找到 choices 字段")
                        return None, None
                except json.JSONDecodeError:
                    print("\n[LLM错误] JSON解析失败")
                    return None, None
        
        else:
            response_data = response.read().decode('utf-8') if not stream else ""
            print(f"\n[LLM错误] HTTP状态码: {response.status}")
            print(f"[LLM错误] 响应内容: {response_data[:500]}")
            return None, None
            
    except Exception as e:
        print(f"\n[LLM错误] 请求异常: {type(e).__name__}: {str(e)}")
        return None, None

def read_file(file_path):
    """读取指定文件的内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        max_length = 3000
        if len(content) > max_length:
            return f"文件内容（前{max_length}字符）:\n{content[:max_length]}\n...\n[内容已截断]"
        return f"文件内容:\n{content}"
    except FileNotFoundError:
        return f"错误：文件不存在 - {file_path}"
    except PermissionError:
        return f"错误：没有权限读取文件 - {file_path}"
    except Exception as e:
        return f"读取文件时发生错误: {type(e).__name__}: {str(e)}"

def write_file(file_path, content, append=False):
    """将内容写入指定文件"""
    try:
        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
        action = "追加" if append else "写入"
        return f"成功{action}文件: {file_path}"
    except PermissionError:
        return f"错误：没有权限写入文件 - {file_path}"
    except Exception as e:
        return f"写入文件时发生错误: {type(e).__name__}: {str(e)}"

def delete_file(file_path):
    """删除指定文件"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return f"成功删除文件: {file_path}"
        else:
            return f"错误：文件不存在 - {file_path}"
    except PermissionError:
        return f"错误：没有权限删除文件 - {file_path}"
    except Exception as e:
        return f"删除文件时发生错误: {type(e).__name__}: {str(e)}"

def list_files(directory):
    """列出指定目录中的文件和子目录"""
    try:
        if os.path.exists(directory):
            files = os.listdir(directory)
            if not files:
                return f"目录为空: {directory}"
            
            result = f"目录内容 ({directory}):\n"
            result += "=" * 40 + "\n"
            for item in files:
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    result += f"[DIR]  {item}\n"
                else:
                    size = os.path.getsize(item_path)
                    result += f"[FILE] {item} ({size} bytes)\n"
            return result
        else:
            return f"错误：目录不存在 - {directory}"
    except PermissionError:
        return f"错误：没有权限访问目录 - {directory}"
    except Exception as e:
        return f"列出目录时发生错误: {type(e).__name__}: {str(e)}"

def list_anythingllm_workspaces():
    """列出所有可用的AnythingLLM工作区"""
    env_vars = load_env()
    api_key = env_vars.get('ANYTHINGLLM_API_KEY', '')
    
    url = "http://localhost:3001/api/v1/workspace"
    
    curl_command = [
        "curl",
        "-X", "GET",
        url,
        "-H", "Content-Type: application/json"
    ]
    
    if api_key:
        curl_command.append("-H")
        curl_command.append(f"Authorization: Bearer {api_key}")
    
    print(f"[系统] 获取工作区列表: {' '.join(shlex.quote(arg) for arg in curl_command)}")
    
    try:
        result = subprocess.run(
            curl_command,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if isinstance(response, list):
                    workspaces = [ws.get('name', ws.get('id', str(i))) for i, ws in enumerate(response)]
                    return f"可用工作区列表:\n" + "\n".join(f"- {ws}" for ws in workspaces)
                return json.dumps(response, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                return f"响应不是JSON格式:\n{result.stdout}"
        else:
            return f"获取工作区列表失败: {result.stderr or result.stdout}"
    
    except subprocess.TimeoutExpired:
        return "请求超时"
    except FileNotFoundError:
        return "未找到curl命令"
    except Exception as e:
        return f"错误: {str(e)}"

def anythingllm_query(message):
    """使用curl调用AnythingLLM的API接口"""
    env_vars = load_env()
    api_key = env_vars.get('ANYTHINGLLM_API_KEY', '')
    
    workspace_name = env_vars.get('ANYTHINGLLM_WORKSPACE', 'ai')
    url = f"http://localhost:3001/api/v1/workspace/{workspace_name}/chat"
    
    data = {
        "message": message
    }
    
    data_json = json.dumps(data, ensure_ascii=False)
    
    curl_command = [
        "curl",
        "-X", "POST",
        url,
        "-H", "Content-Type: application/json",
        "-d", data_json
    ]
    
    if api_key:
        curl_command.insert(-2, "-H")
        curl_command.insert(-2, f"Authorization: Bearer {api_key}")
    
    print(f"[系统] 执行curl命令: {' '.join(shlex.quote(arg) for arg in curl_command)}")
    
    try:
        result = subprocess.run(
            curl_command,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8'
        )
        
        stdout_content = result.stdout if result.stdout else ""
        stderr_content = result.stderr if result.stderr else ""
        
        if result.returncode == 0:
            try:
                if not stdout_content:
                    return "API返回空响应"
                
                response = json.loads(stdout_content)
                
                if 'error' in response and response['error'] is not None:
                    error_msg = response['error']
                    full_response = json.dumps(response, ensure_ascii=False, indent=2)
                    if error_msg and isinstance(error_msg, str) and 'not a valid workspace' in error_msg:
                        return f"错误：工作区名称无效\n详细信息: {error_msg}\n完整响应:\n{full_response}\n请检查工作区名称是否正确，或访问 http://localhost:3001/api/docs/ 查看API文档"
                    return f"API返回错误: {error_msg if error_msg else '未知错误'}\n完整响应:\n{full_response}"
                
                if response.get('type') == 'abort':
                    error_info = response.get('error', '未知错误')
                    return f"查询被中止\n详细信息: {error_info}\n请检查工作区配置"
                
                if response.get('type') == 'textResponse' and response.get('textResponse'):
                    return response['textResponse']
                
                return json.dumps(response, ensure_ascii=False, indent=2)
            except json.JSONDecodeError as e:
                return f"JSON解析失败: {str(e)}\n响应内容:\n{stdout_content[:500]}"
        else:
            error_msg = f"curl命令执行失败 (代码: {result.returncode})\n"
            if stderr_content:
                error_msg += f"错误信息: {stderr_content[:500]}\n"
            if stdout_content:
                error_msg += f"响应内容: {stdout_content[:500]}\n"
            error_msg += "请查看 http://localhost:3001/api/docs/ 获取API文档"
            return error_msg
    
    except subprocess.TimeoutExpired:
        return "curl命令执行超时，请检查网络连接或API服务状态"
    except FileNotFoundError:
        return "未找到curl命令，请确保curl已安装并添加到系统路径"
    except Exception as e:
        return f"执行curl命令时发生错误: {type(e).__name__}: {str(e)}"

def extract_5w_info(messages):
    """从聊天记录中提取5W关键信息"""
    conversation_text = ""
    for msg in messages:
        role = "用户" if msg['role'] == 'user' else "助手"
        conversation_text += f"{role}: {msg.get('content', '')}\n"
    
    prompt = f"""请从以下对话中提取详细的关键信息，按照5W规则提取：
- Who（谁）：参与对话的人物，尽可能具体
- What（做了什么）：详细描述主要事件或讨论内容，包括具体话题和问题
- When（什么时候）：时间信息（如果有）
- Where（在哪里）：地点信息（如果有）
- Why（为什么）：详细说明原因或目的

请以JSON格式输出，只输出JSON，不要有其他内容：
{{
    "who": "人物",
    "what": "详细的事件描述",
    "when": "时间（无则为空）",
    "where": "地点（无则为空）",
    "why": "详细的原因说明"
}}

对话内容：
{conversation_text}
"""
    
    messages_for_extraction = [
        {"role": "system", "content": "你是一个专业的信息提取助手，擅长从对话中提取详细的关键信息。"},
        {"role": "user", "content": prompt}
    ]
    
    env_vars = load_env()
    result, _ = llm_request(env_vars, messages_for_extraction)
    
    info = {"who": "用户与助手", "what": "对话交流", "when": "", "where": "", "why": "", "content": conversation_text}
    
    if result:
        try:
            llm_info = json.loads(result)
            info.update(llm_info)
        except json.JSONDecodeError:
            info["what"] = result
    
    info["content"] = conversation_text
    return info

def log_5w_info(info):
    """将5W信息记录到日志文件"""
    log_dir = r"D:\chat-log"
    log_file = os.path.join(log_dir, "log.txt")
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"[系统] 创建目录: {log_dir}")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = f"\n{'='*50}\n"
    log_entry += f"时间: {timestamp}\n"
    log_entry += f"Who（谁）: {info.get('who', '')}\n"
    log_entry += f"What（做了什么）: {info.get('what', '')}\n"
    log_entry += f"When（什么时候）: {info.get('when', '')}\n"
    log_entry += f"Where（在哪里）: {info.get('where', '')}\n"
    log_entry += f"Why（为什么）: {info.get('why', '')}\n"
    log_entry += f"--- 对话内容 ---\n"
    log_entry += f"{info.get('content', '')}\n"
    log_entry += f"{'='*50}\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    print(f"[系统] 5W信息已记录到: {log_file}")

def search_history(query):
    """搜索聊天历史记录"""
    log_file = r"D:\chat-log\log.txt"
    
    if not os.path.exists(log_file):
        return "未找到聊天历史记录文件。"
    
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    max_content_length = 3000
    if len(content) > max_content_length:
        print(f"[系统] 日志内容过长 ({len(content)} 字符)，进行截断")
        content = content[-max_content_length:] + "\n...(内容已截断，仅显示最近部分)"
    
    return content

def should_search_history(user_input):
    """判断是否需要搜索聊天历史"""
    user_input = user_input.strip().lower()
    
    if user_input.startswith('/search'):
        return True
    
    keywords = ['查找聊天历史', '搜索历史', '历史记录', '查记录', '聊天记录']
    for keyword in keywords:
        if keyword in user_input:
            return True
    
    return False

def extract_search_query(user_input):
    """提取搜索关键词"""
    if user_input.startswith('/search'):
        return user_input[7:].strip()
    return user_input

def parse_function_call(response):
    """解析工具调用"""
    if '<function_calls>' in response and '</function_calls>' in response:
        start = response.find('<function_calls>') + len('<function_calls>')
        end = response.find('</function_calls>')
        json_str = response[start:end].strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    return None

def curl_url(url):
    """通过HTTP访问指定URL并返回网页内容"""
    try:
        import urllib.parse
        
        parsed_url = urlparse(url)
        host = parsed_url.hostname or parsed_url.netloc
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        
        path = parsed_url.path or '/'
        path = urllib.parse.quote(path, safe='/')
        
        query = ''
        if parsed_url.query:
            query = urllib.parse.quote(parsed_url.query, safe='=&')
        
        full_path = path + ('?' + query if query else '')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'close'
        }
        
        if parsed_url.scheme == 'https':
            conn = http.client.HTTPSConnection(host, port, timeout=30)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=30)
        
        try:
            conn.request("GET", full_path, headers=headers)
            response = conn.getresponse()
            
            status = response.status
            content_type = response.getheader('Content-Type', '')
            
            data = response.read()
            
            try:
                content = data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = data.decode('gbk')
                except UnicodeDecodeError:
                    content = data.decode('latin-1')
            
            if 'text/html' in content_type:
                clean_content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
                clean_content = re.sub(r'<script[^>]*>.*?</script>', '', clean_content, flags=re.DOTALL | re.IGNORECASE)
                clean_content = re.sub(r'<[^>]+>', '', clean_content)
                clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                content = clean_content[:5000] + ('...' if len(clean_content) > 5000 else '')
            
            result = f"HTTP状态码: {status}\n内容类型: {content_type}\n内容: {content}"
            return result
        finally:
            conn.close()
            
    except Exception as e:
        return f"错误: {str(e)}"

def execute_tool(func_call, user_input):
    """执行工具调用并返回结果"""
    tool_name = func_call['name']
    args = func_call.get('arguments', {})
    
    print(f"\n--- 检测到工具调用 ---")
    print(f"工具名称: {tool_name}")
    print(f"参数: {json.dumps(args, ensure_ascii=False)}")
    
    if tool_name == 'anythingllm_query':
        message = args.get('message', '')
        print(f"\n[系统] 正在调用AnythingLLM查询...")
        return anythingllm_query(message)
    
    elif tool_name == 'read_file':
        file_path = args.get('file_path', args.get('path', ''))
        print(f"\n[系统] 正在读取文件: {file_path}")
        return read_file(file_path)
    
    elif tool_name == 'write_file':
        file_path = args.get('file_path', args.get('path', args.get('file', '')))
        content = args.get('content', '')
        append = args.get('append', False)
        print(f"\n[系统] 正在写入文件: {file_path}")
        return write_file(file_path, content, append)
    
    elif tool_name == 'delete_file':
        file_path = args.get('file_path', args.get('path', ''))
        print(f"\n[系统] 正在删除文件: {file_path}")
        return delete_file(file_path)
    
    elif tool_name == 'list_files':
        directory = args.get('directory', args.get('path', args.get('directory_path', '')))
        print(f"\n[系统] 正在列出目录: {directory}")
        return list_files(directory)
    
    elif tool_name == 'use_skill':
        skill_name = args.get('skill_name', '')
        print(f"\n[系统] 正在加载技能: {skill_name}")
        skill_content = load_skill_content(skill_name)
        print(f"\n技能内容:\n{skill_content}")
        
        env_vars = load_env()
        skill_messages = [
            {"role": "system", "content": f"请按照以下技能内容执行任务：\n\n{skill_content}"},
            {"role": "user", "content": user_input}
        ]
        skill_response, _ = llm_request(env_vars, skill_messages)
        
        if skill_response:
            return skill_response
        else:
            return "技能执行失败"
    
    elif tool_name == 'search_history':
        query = args.get('query', '')
        print(f"\n[系统] 正在搜索聊天历史: {query}")
        return search_history(query)
    
    elif tool_name == 'curl_url':
        url = args.get('url', '')
        print(f"\n[系统] 正在访问URL: {url}")
        return curl_url(url)
    
    else:
        return f"未知工具: {tool_name}"

def build_analysis_prompt(user_input: str, call_history: list, available_tools: list) -> str:
    """
    构建分析提示词，用于指导LLM进行链式工具调用决策
    
    Args:
        user_input: 用户的原始请求
        call_history: 已执行的工具调用历史列表
        available_tools: 可用工具列表
    
    Returns:
        str: 构建好的分析提示词
    """
    # 1. 用户原始请求
    prompt = f"用户请求: {user_input}\n\n"
    
    # 2. 已执行的工具调用历史
    if call_history:
        prompt += "已执行步骤:\n"
        for i, call in enumerate(call_history, 1):
            tool_name = call.get('tool_name', '')
            arguments = call.get('arguments', {})
            result = call.get('result', '')
            
            # 截断过长的结果
            result_str = str(result)
            if len(result_str) > 100:
                result_str = result_str[:100] + "..."
            
            prompt += f"{i}. 工具: {tool_name}\n"
            prompt += f"   参数: {json.dumps(arguments, ensure_ascii=False)}\n"
            prompt += f"   结果: {result_str}\n\n"
    else:
        prompt += "已执行步骤: 无\n\n"
    
    # 3. 决策规则说明
    prompt += "决策规则:\n"
    prompt += "1. 分析用户请求和已执行步骤的结果\n"
    prompt += "2. 判断是否需要继续调用工具或可以直接回答\n"
    prompt += "3. 如果已有足够信息回答用户问题，直接给出最终回答\n"
    prompt += "4. 如果需要更多信息，选择合适的工具进行调用\n"
    prompt += "5. 当已经读取了文件内容后，应该立即总结文件的主要内容，不要重复读取同一文件\n"
    prompt += "6. 用户请求'查找practice07目录下所有包含def关键词的文件，并总结这些文件的主要内容'时，\n"
    prompt += "   如果已经读取了文件内容，应该直接总结，不需要继续调用工具\n"
    prompt += "7. 如果用户请求创建文件并写入内容，必须调用write_file工具来实际写入文件，\n"
    prompt += "   不能只口头回答说已创建文件\n"
    prompt += "8. 在完成写入操作后，才能给出最终回答\n"
    prompt += "9. 如果用户请求访问网页并总结内容，应该：\n"
    prompt += "   a) 首先调用curl_url工具访问指定URL\n"
    prompt += "   b) 然后根据网页内容进行总结\n"
    prompt += "   c) 最后调用write_file工具保存总结内容\n"
    prompt += "10. 在完成所有操作后，才能给出最终回答\n"
    prompt += "11. 可用工具列表:\n"
    
    for tool in available_tools:
        prompt += f"   - {tool['name']}: {tool['description']}\n"
    
    # 4. JSON输出格式要求
    prompt += "\n输出格式要求:\n"
    prompt += "请严格按照以下JSON格式输出决策结果:\n\n"
    prompt += "完成任务时（可以直接回答用户）:\n"
    prompt += "{\n"
    prompt += '  "done": true,\n'
    prompt += '  "answer": "最终回答内容"\n'
    prompt += "}\n\n"
    prompt += "继续调用工具时（需要获取更多信息）:\n"
    prompt += "{\n"
    prompt += '  "done": false,\n'
    prompt += '  "toolcall": {\n'
    prompt += '    "name": "工具名称",\n'
    prompt += '    "arguments": {"参数名": "参数值"}\n'
    prompt += "  }\n"
    prompt += "}\n\n"
    prompt += "注意: 输出必须是有效的JSON格式，不要包含其他任何内容！"
    
    return prompt

def parse_decision_response(response: str) -> dict:
    """
    解析LLM返回的决策响应
    
    Args:
        response: LLM的响应内容
    
    Returns:
        dict: 解析后的决策字典，包含done和answer/toolcall字段
    """
    try:
        # 清理响应，移除可能的前后引号或其他字符
        response = response.strip()
        
        # 处理可能的markdown代码块
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]
        
        response = response.strip()
        
        # 尝试解析JSON
        try:
            decision = json.loads(response)
        except json.JSONDecodeError:
            # 如果标准解析失败，尝试修复包含换行符的JSON
            # 将字符串值中的换行符转义
            import re
            # 匹配双引号内的内容并转义换行符
            fixed_response = re.sub(
                r'"([^"]*?)"',
                lambda m: '"' + m.group(1).replace('\n', '\\n').replace('\r', '\\r') + '"',
                response
            )
            decision = json.loads(fixed_response)
        
        if 'done' in decision:
            return decision
        else:
            return None
            
    except json.JSONDecodeError as e:
        print(f"[解析错误] JSON解析失败: {str(e)}")
        return None
    except Exception as e:
        print(f"[解析错误] 解析响应时发生错误: {str(e)}")
        return None

def execute_chained_tool_call(user_input: str, env_vars: dict, max_iterations: int = 5) -> tuple:
    """
    执行链式工具调用的完整流程
    
    Args:
        user_input: 用户的原始请求
        env_vars: 环境变量配置
        max_iterations: 最大迭代次数，默认5次
    
    Returns:
        tuple: (最终回答, 上下文对象)
    """
    print(f"\n[链式调用] 开始执行链式工具调用，最大迭代次数: {max_iterations}")
    
    # 获取可用工具列表
    available_tools = [
        {
            "name": "search_history",
            "description": "搜索聊天历史记录"
        },
        {
            "name": "anythingllm_query",
            "description": "向AnythingLLM查询数据"
        },
        {
            "name": "read_file",
            "description": "读取指定文件的内容"
        },
        {
            "name": "write_file",
            "description": "将内容写入指定文件"
        },
        {
            "name": "delete_file",
            "description": "删除指定文件"
        },
        {
            "name": "list_files",
            "description": "列出指定目录中的文件和子目录"
        },
        {
            "name": "use_skill",
            "description": "使用指定的技能"
        }
    ]
    
    # 1. 创建上下文管理器
    context = ChainedCallContext(max_iterations=max_iterations)
    
    # 2. 循环执行链式调用
    while not context.is_chained_call_complete():
        try:
            # 获取已执行的工具调用历史
            call_history = context.get_call_history()
            
            # 3. 构建分析提示词(包含用户请求、已执行步骤历史、决策规则、输出格式要求)
            analysis_prompt = build_analysis_prompt(user_input, call_history, available_tools)
            
            # 4. 调用LLM决定下一步操作
            print(f"\n[链式调用] 第 {context.get_iteration_count() + 1} 轮 - 调用LLM分析...")
            
            messages = [
                {"role": "system", "content": "你是一个智能决策助手，负责分析用户请求并决定是否需要调用工具或直接回答。"},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response, usage = llm_request(env_vars, messages)
            
            if not response:
                print("[链式调用] LLM返回空响应，结束链式调用")
                break
            
            print(f"[链式调用] LLM响应: {response[:150]}..." if len(response) > 150 else f"[链式调用] LLM响应: {response}")
            
            # 5. 解析LLM响应(JSON格式)
            decision = parse_decision_response(response)
            
            if not decision:
                print("[链式调用] 无法解析LLM响应，尝试使用原有的工具调用格式")
                # 降级到原有的工具调用格式解析
                func_call = parse_function_call(response)
                if func_call:
                    decision = {
                        "done": False,
                        "toolcall": {
                            "name": func_call['name'],
                            "arguments": func_call.get('arguments', {})
                        }
                    }
                else:
                    # 如果无法解析，假设LLM直接给出了答案
                    decision = {"done": True, "answer": response}
            
            # 6. 根据决策执行
            if decision.get('done'):
                # 如果任务完成，返回最终回答
                final_answer = decision.get('answer', '未获得回答')
                print(f"[链式调用] 任务完成，最终回答: {final_answer[:50]}...")
                context.set_complete(final_answer)
                break
            else:
                # 如果需要继续调用工具
                toolcall = decision.get('toolcall', {})
                tool_name = toolcall.get('name', '')
                arguments = toolcall.get('arguments', {})
                
                if not tool_name:
                    print("[链式调用] 工具名称为空，结束链式调用")
                    break
                
                # 记录工具调用开始
                context.start_call(tool_name, arguments)
                
                # 执行工具
                print(f"[链式调用] 执行工具: {tool_name}")
                tool_result = execute_tool({"name": tool_name, "arguments": arguments}, user_input)
                
                # 记录工具调用结束
                context.end_call(tool_name, tool_result)
                
                # 存储中间变量
                context.store_variable(f"result_{context.get_iteration_count()}", tool_result)
                
                # 检查上下文长度并自动压缩
                context_length = context.get_context_length()
                if context_length > context.max_context_chars:
                    print(f"[链式调用] 上下文长度 {context_length} 超过限制 {context.max_context_chars}，进行压缩")
                    context.compress_context()
                
                print(f"[链式调用] 工具执行完成，结果已保存")
                
        except StopIteration as e:
            print(f"\n[链式调用] {e}")
            break
        except Exception as e:
            print(f"\n[链式调用] 执行过程中发生错误: {type(e).__name__}: {str(e)}")
            break
    
    # 返回最终结果
    final_result = context.final_result or "链式调用完成，但未获得最终回答"
    return final_result, context

def main():
    env_vars = load_env()
    history = []
    user_round_count = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_time = 0
    
    print("欢迎使用链式工具调用聊天客户端！")
    print("支持链式工具调用：前一个工具的输出可以作为后一个工具的输入")
    print("使用 /search 关键词 来搜索聊天历史")
    print("使用 /workspaces 列出所有AnythingLLM工作区")
    print("支持文件操作：读取、写入、删除、列出目录")
    print("支持技能调用：使用 use_skill 工具")
    print("使用 anythingllm 查询知识库")
    print("按 Ctrl+C 退出\n")
    
    try:
        while True:
            user_input = input("你: ")
            
            if not user_input.strip():
                continue
            
            user_round_count += 1
            history.append({"role": "user", "content": user_input})
            
            if should_search_history(user_input):
                query = extract_search_query(user_input)
                history.append({"role": "system", "content": "正在搜索聊天历史..."})
                
                history_content = search_history(query)
                
                search_messages = [
                    {"role": "system", "content": "你是一个聊天历史分析助手。请根据提供的聊天历史记录回答用户的问题。"},
                    {"role": "user", "content": f"聊天历史记录:\n{history_content}\n\n用户问题: {query}"}
                ]
                
                response, usage = llm_request(env_vars, search_messages)
                
                if response:
                    print(f"AI: {response}")
                    history.append({"role": "assistant", "content": response})
                    if usage:
                        total_prompt_tokens += usage.get('prompt_tokens', 0)
                        total_completion_tokens += usage.get('completion_tokens', 0)
                else:
                    print("AI: 搜索失败")
                    history.append({"role": "assistant", "content": "搜索失败"})
                
                print(f"\n[统计] 提示词: {total_prompt_tokens} | 回复: {total_completion_tokens} | 累计: {total_prompt_tokens + total_completion_tokens}")
                print("-" * 60)
                continue
            
            # 使用链式调用执行函数
            final_result, context = execute_chained_tool_call(user_input, env_vars, max_iterations=5)
            
            print(f"AI: {final_result}")
            history.append({"role": "assistant", "content": final_result})
            
            print(f"\n{context.get_summary()}")
            
            speed = (total_prompt_tokens + total_completion_tokens) / total_time if total_time > 0 else 0
            print(f"\n[统计] 提示词: {total_prompt_tokens} | 回复: {total_completion_tokens} | 累计: {total_prompt_tokens + total_completion_tokens} | 速度: {speed:.2f} token/s")
            print("-" * 60)
            
            if user_round_count % 5 == 0:
                print(f"\n[系统] 已完成 {user_round_count} 轮对话，开始提取关键信息...")
                recent_messages = history[-10:]
                info = extract_5w_info(recent_messages)
                log_5w_info(info)
                print(f"[系统] 关键信息提取完成")
    
    except KeyboardInterrupt:
        print("\n\n退出程序...")
        total_tokens = total_prompt_tokens + total_completion_tokens
        avg_speed = total_tokens / total_time if total_time > 0 else 0
        print(f"\n[会话统计]")
        print(f"总提示词token: {total_prompt_tokens}")
        print(f"总回复token: {total_completion_tokens}")
        print(f"总token: {total_tokens}")
        print(f"总耗时: {total_time:.2f}s")
        print(f"平均速度: {avg_speed:.2f} token/s")
        print(f"对话轮数: {user_round_count}")

if __name__ == "__main__":
    main()
