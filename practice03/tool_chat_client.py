import os
import json
import time
import sys
import http.client
from urllib.parse import urlparse
from datetime import datetime


def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(env_path):
        print(f"错误: .env文件不存在，请从env.example复制并填写正确参数")
        return None
    
    env_vars = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    required_vars = ['LLM_BASE_URL', 'LLM_MODEL', 'LLM_API_KEY']
    for var in required_vars:
        if var not in env_vars:
            print(f"错误: 缺少必要的环境变量 {var}")
            return None
    
    return env_vars


def list_files(directory):
    """列出目录下的文件信息"""
    try:
        files = []
        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            stat = os.stat(full_path)
            
            file_info = {
                'name': entry,
                'path': full_path,
                'size': stat.st_size,
                'size_human': format_size(stat.st_size),
                'is_directory': os.path.isdir(full_path),
                'last_modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'creation_time': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            }
            files.append(file_info)
        
        return json.dumps(files, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"错误: {str(e)}"


def format_size(size_bytes):
    """格式化文件大小为人类可读格式"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"


def rename_file(old_path, new_name):
    """重命名文件"""
    try:
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)
        os.rename(old_path, new_path)
        return f"文件已重命名为: {new_path}"
    except Exception as e:
        return f"错误: {str(e)}"


def delete_file(file_path):
    """删除文件"""
    try:
        os.remove(file_path)
        return f"文件已删除: {file_path}"
    except Exception as e:
        return f"错误: {str(e)}"


def create_file(directory, filename, content):
    """创建新文件并写入内容"""
    try:
        full_path = os.path.join(directory, filename)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"文件已创建: {full_path}"
    except Exception as e:
        return f"错误: {str(e)}"


def read_file(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"错误: {str(e)}"


def curl_url(url, extract_text=True):
    """通过HTTP访问指定URL并返回网页内容"""
    try:
        import urllib.parse
        import re
        
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
        
        conn.request('GET', full_path, headers=headers)
        response = conn.getresponse()
        
        status_code = response.status
        content_type = response.getheader('Content-Type', '')
        
        if status_code == 200:
            content = response.read().decode('utf-8', errors='ignore')
            conn.close()
            
            if extract_text and 'text/html' in content_type.lower():
                content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', content, flags=re.IGNORECASE)
                content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', content, flags=re.IGNORECASE)
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'[\r\n]+', '\n', content)
                content = re.sub(r'[ \t]+', ' ', content)
                content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
            
            return f"HTTP状态码: {status_code}\n内容类型: {content_type}\n\n内容:\n{content[:5000]}"
        else:
            content = response.read().decode('utf-8', errors='ignore')
            conn.close()
            return f"HTTP状态码: {status_code}\n错误信息: {content}"
            
    except Exception as e:
        error_msg = f"错误: {str(e)}"
        if 'getaddrinfo failed' in error_msg:
            error_msg += "\n提示: 可能是域名解析失败，请检查URL是否正确，确保网络连接正常"
        return error_msg


def get_weather(city):
    """查询指定城市的天气信息，包含最高温和最低温"""
    try:
        import urllib.parse
        
        encoded_city = urllib.parse.quote(city)
        url = f"https://wttr.in/{encoded_city}?format=j1"
        
        parsed_url = urlparse(url)
        host = parsed_url.hostname or parsed_url.netloc
        port = parsed_url.port or 443
        path = parsed_url.path or '/'
        if parsed_url.query:
            path += '?' + parsed_url.query
        
        headers = {
            'User-Agent': 'curl/7.68.0',
            'Accept': 'application/json',
            'Connection': 'close'
        }
        
        conn = http.client.HTTPSConnection(host, port, timeout=30)
        conn.request('GET', path, headers=headers)
        response = conn.getresponse()
        
        if response.status == 200:
            content = response.read().decode('utf-8', errors='ignore')
            conn.close()
            
            try:
                weather_data = json.loads(content)
                
                current_condition = weather_data.get('current_condition', [])[0] if weather_data.get('current_condition') else {}
                nearest_area = weather_data.get('nearest_area', [])[0] if weather_data.get('nearest_area') else {}
                forecast = weather_data.get('weather', [])[0] if weather_data.get('weather') else {}
                
                location = nearest_area.get('areaName', [{}])[0].get('value', city)
                weather_desc = current_condition.get('weatherDesc', [{}])[0].get('value', '')
                temp_c = current_condition.get('temp_C', '')
                feels_like = current_condition.get('FeelsLikeC', '')
                humidity = current_condition.get('humidity', '')
                wind = current_condition.get('windspeedKmph', '')
                
                max_temp = forecast.get('maxtempC', '')
                min_temp = forecast.get('mintempC', '')
                uv_index = forecast.get('uvIndex', '')
                
                result = f"📍 {location} 天气\n"
                result += "─" * 30 + "\n"
                result += f"当前天气: {weather_desc}\n"
                result += f"当前温度: {temp_c}°C (体感 {feels_like}°C)\n"
                result += f"最高温度: {max_temp}°C\n"
                result += f"最低温度: {min_temp}°C\n"
                result += f"湿度: {humidity}%\n"
                result += f"风速: {wind} km/h\n"
                result += f"紫外线指数: {uv_index}"
                
                return result
            
            except json.JSONDecodeError:
                return f"📍 {city} 天气\nJSON解析失败"
        else:
            content = response.read().decode('utf-8', errors='ignore')
            conn.close()
            return f"查询失败，HTTP状态码: {response.status}\n{content}"
            
    except Exception as e:
        return f"天气查询错误: {str(e)}"


def execute_tool_call(tool_name, arguments):
    """执行工具调用"""
    tool_map = {
        'list_files': list_files,
        'rename_file': rename_file,
        'delete_file': delete_file,
        'create_file': create_file,
        'read_file': read_file,
        'curl_url': curl_url,
        'get_weather': get_weather
    }
    
    if tool_name not in tool_map:
        return f"未知工具: {tool_name}"
    
    try:
        func = tool_map[tool_name]
        result = func(**arguments)
        return result
    except Exception as e:
        return f"工具调用错误: {str(e)}"


def get_system_prompt():
    """获取包含工具描述的系统提示词"""
    tools = [
        {
            "name": "list_files",
            "description": "列出指定目录下的所有文件和子目录，返回文件的详细信息包括名称、路径、大小、是否为目录、最后修改时间等",
            "parameters": {
                "directory": {
                    "type": "string",
                    "description": "要列出的目录路径",
                    "required": True
                }
            }
        },
        {
            "name": "rename_file",
            "description": "重命名指定路径的文件",
            "parameters": {
                "old_path": {
                    "type": "string",
                    "description": "文件的当前完整路径",
                    "required": True
                },
                "new_name": {
                    "type": "string",
                    "description": "文件的新名称",
                    "required": True
                }
            }
        },
        {
            "name": "delete_file",
            "description": "删除指定路径的文件",
            "parameters": {
                "file_path": {
                    "type": "string",
                    "description": "要删除的文件完整路径",
                    "required": True
                }
            }
        },
        {
            "name": "create_file",
            "description": "在指定目录下创建新文件并写入内容",
            "parameters": {
                "directory": {
                    "type": "string",
                    "description": "要创建文件的目录路径",
                    "required": True
                },
                "filename": {
                    "type": "string",
                    "description": "新文件的名称",
                    "required": True
                },
                "content": {
                    "type": "string",
                    "description": "要写入文件的内容",
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
                    "description": "要读取的文件完整路径",
                    "required": True
                }
            }
        },
        {
            "name": "curl_url",
            "description": "通过HTTP/HTTPS访问指定URL并返回网页内容",
            "parameters": {
                "url": {
                    "type": "string",
                    "description": "要访问的网页URL地址，如https://example.com",
                    "required": True
                }
            }
        },
        {
            "name": "get_weather",
            "description": "查询指定城市的天气信息",
            "parameters": {
                "city": {
                    "type": "string",
                    "description": "要查询天气的城市名称，如北京、上海、Guangzhou",
                    "required": True
                }
            }
        }
    ]
    
    system_prompt = f"""你是一个具有工具调用能力的AI助手。你可以使用以下工具来完成任务：

可用工具列表：
{json.dumps(tools, ensure_ascii=False, indent=2)}

当你需要使用工具时，请按照以下JSON格式输出：
<function_calls>
{{
    "name": "工具名称",
    "arguments": {{
        "参数名": "参数值"
    }}
}}
</function_calls>

请记住：
1. 只能使用上述列出的工具
2. 工具调用必须严格按照指定的JSON格式，并用<function_calls>和</function_calls>包裹
3. 如果不需要调用工具，可以直接回答问题
4. 参数值必须是有效的路径和文件名
5. 路径可以是绝对路径或相对路径，相对路径相对于当前工作目录

请根据用户的问题决定是否需要调用工具。"""
    
    return system_prompt


def stream_llm_response(env_vars, messages):
    """流式调用LLM"""
    parsed_url = urlparse(env_vars['LLM_BASE_URL'])
    host = parsed_url.hostname or parsed_url.netloc
    port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
    path = parsed_url.path or '/'
    if not path.endswith('/'):
        path += '/'
    path += 'chat/completions'
    
    data = json.dumps({
        "model": env_vars.get('LLM_MODEL', 'gpt-3.5-turbo'),
        "messages": messages,
        "max_tokens": int(env_vars.get('LLM_MAX_TOKENS', 2000)),
        "temperature": float(env_vars.get('LLM_TEMPERATURE', 0.7)),
        "stream": True
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {env_vars['LLM_API_KEY']}"
    }
    
    try:
        if parsed_url.scheme == 'https':
            conn = http.client.HTTPSConnection(host, port, timeout=30)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=30)
        
        conn.request('POST', path, data, headers)
        response = conn.getresponse()
        
        if response.status != 200:
            response_data = response.read().decode('utf-8')
            conn.close()
            try:
                error_json = json.loads(response_data)
                if 'error' in error_json:
                    print(f"\nAPI错误: {error_json['error'].get('message', response_data)}")
                else:
                    print(f"\n请求失败: 状态码 {response.status}")
            except:
                print(f"\n请求失败: {response_data}")
            return None, None
        
        buffer = ''
        full_content = ''
        prompt_tokens = 0
        completion_tokens = 0
        
        print("\nAI: ", end='', flush=True)
        
        while True:
            chunk = response.read(1024)
            if not chunk:
                break
            
            buffer += chunk.decode('utf-8', errors='ignore')
            
            while '\n\n' in buffer:
                line, buffer = buffer.split('\n\n', 1)
                lines = line.split('\n')
                
                for l in lines:
                    l = l.strip()
                    if l.startswith('data: '):
                        data_str = l[6:]
                        if data_str == '[DONE]':
                            conn.close()
                            
                            if completion_tokens == 0 and full_content:
                                completion_tokens = len(full_content) // 4
                            
                            if prompt_tokens == 0:
                                for msg in messages:
                                    prompt_tokens += len(msg.get('content', '')) // 4
                            
                            return full_content, {
                                'prompt_tokens': prompt_tokens,
                                'completion_tokens': completion_tokens,
                                'total_tokens': prompt_tokens + completion_tokens
                            }
                        
                        try:
                            if data_str:
                                obj = json.loads(data_str)
                                
                                if 'usage' in obj:
                                    prompt_tokens = obj['usage'].get('prompt_tokens', prompt_tokens)
                                    completion_tokens = obj['usage'].get('completion_tokens', completion_tokens)
                                
                                if obj.get('choices'):
                                    delta = obj['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        sys.stdout.write(content)
                                        sys.stdout.flush()
                                        full_content += content
                                
                                if obj['choices'][0].get('usage'):
                                    prompt_tokens = obj['choices'][0]['usage'].get('prompt_tokens', prompt_tokens)
                                    completion_tokens = obj['choices'][0]['usage'].get('completion_tokens', completion_tokens)
                        
                        except json.JSONDecodeError:
                            continue
        
        conn.close()
        
        if completion_tokens == 0 and full_content:
            completion_tokens = len(full_content) // 4
        
        if prompt_tokens == 0:
            for msg in messages:
                prompt_tokens += len(msg.get('content', '')) // 4
        
        return full_content, {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens
        }
    
    except Exception as e:
        print(f"\n错误: {str(e)}")
        return None, None


def parse_tool_call(content):
    """解析LLM响应中的工具调用"""
    start_tag = '<function_calls>'
    end_tag = '</function_calls>'
    
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)
    
    if start_idx != -1 and end_idx != -1:
        try:
            tool_json = content[start_idx + len(start_tag):end_idx].strip()
            return json.loads(tool_json)
        except json.JSONDecodeError:
            return None
    
    return None


def main():
    env_vars = load_env()
    if not env_vars:
        return
    
    print("=== LLM工具调用客户端 ===")
    print("输入消息开始聊天，支持工具调用")
    print("可用工具: list_files, rename_file, delete_file, create_file, read_file, curl_url, get_weather")
    print("按 Ctrl+C 退出")
    print("=" * 60)
    
    history = []
    system_prompt = get_system_prompt()
    history.append({"role": "system", "content": system_prompt})
    
    total_prompt_tokens = 0
    total_completion_tokens = 0
    start_time = time.time()
    
    try:
        while True:
            try:
                user_input = input("\n你: ").strip()
            except EOFError:
                break
            
            if not user_input:
                print("请输入内容")
                continue
            
            history.append({"role": "user", "content": user_input})
            
            content, usage = stream_llm_response(env_vars, history)
            
            if content:
                history.append({"role": "assistant", "content": content})
                
                tool_call = parse_tool_call(content)
                if tool_call:
                    print("\n--- 检测到工具调用 ---")
                    print(f"工具名称: {tool_call['name']}")
                    print(f"参数: {json.dumps(tool_call['arguments'], ensure_ascii=False)}")
                    
                    result = execute_tool_call(tool_call['name'], tool_call['arguments'])
                    print("\n工具执行结果:")
                    print(result)
                    
                    history.append({"role": "user", "content": f"工具执行结果:\n{result}"})
                
                if usage:
                    total_prompt_tokens += usage['prompt_tokens']
                    total_completion_tokens += usage['completion_tokens']
                    
                    elapsed_time = time.time() - start_time
                    total_tokens = total_prompt_tokens + total_completion_tokens
                    tokens_per_second = total_tokens / elapsed_time if elapsed_time > 0 else 0
                    
                    print(f"\n[统计] 提示词: {usage['prompt_tokens']} | 回复: {usage['completion_tokens']} | "
                          f"累计: {total_tokens} | 速度: {tokens_per_second:.2f} token/s")
            
            print("-" * 60)
    
    except KeyboardInterrupt:
        print("\n\n感谢使用！再见！")
        
        elapsed_time = time.time() - start_time
        total_tokens = total_prompt_tokens + total_completion_tokens
        
        print("\n=== 会话统计 ===")
        print(f"提示词token: {total_prompt_tokens}")
        print(f"回复token: {total_completion_tokens}")
        print(f"总token: {total_tokens}")
        print(f"会话时长: {elapsed_time:.2f} 秒")
        print(f"平均速度: {total_tokens / elapsed_time:.2f} token/秒")


if __name__ == "__main__":
    main()