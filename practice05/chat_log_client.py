import http.client
import json
import os
import time
import re
from urllib.parse import urlparse, quote
from datetime import datetime

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
    return env_vars

def get_system_prompt():
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
        }
    ]
    
    system_prompt = f"""你是一个聊天助手，具有搜索聊天历史的能力。

可用工具:
{json.dumps(tools, ensure_ascii=False, indent=2)}

工具调用格式:
<function_calls>
{{
    "name": "工具名称",
    "arguments": {{
        "参数名": "参数值"
    }}
}}
</function_calls>

规则:
1. 如果用户消息以"/search"开头，或者表达了"查找聊天历史"的意思，调用search_history工具
2. 调用工具时必须使用<function_calls>标签包裹
3. 参数必须是JSON格式
4. 如果不需要调用工具，可以直接回答问题"""
    
    return system_prompt

def llm_request(env_vars, messages, stream=False):
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
        'max_tokens': 2048,
        'temperature': 0.7
    }
    
    try:
        if parsed_url.scheme == 'https':
            conn = http.client.HTTPSConnection(host, port, timeout=60)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=60)
        
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        conn.request('POST', path, body=body, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
        
        if response.status == 200:
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
            print(f"\n[LLM错误] HTTP状态码: {response.status}")
            print(f"[LLM错误] 响应内容: {response_data[:500]}")
            return None, None
            
    except Exception as e:
        print(f"\n[LLM错误] 请求异常: {type(e).__name__}: {str(e)}")
        return None, None

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

def main():
    env_vars = load_env()
    history = []
    user_round_count = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_time = 0
    
    print("欢迎使用聊天日志客户端！")
    print("使用 /search 关键词 来搜索聊天历史")
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
            
            messages = [{"role": "system", "content": get_system_prompt()}] + history
            
            start_time = time.time()
            response, usage = llm_request(env_vars, messages)
            elapsed_time = time.time() - start_time
            
            if usage:
                total_prompt_tokens += usage.get('prompt_tokens', 0)
                total_completion_tokens += usage.get('completion_tokens', 0)
            total_time += elapsed_time
            
            if response:
                print(f"AI: {response}")
                history.append({"role": "assistant", "content": response})
            else:
                print("AI: 无法获取响应")
                history.append({"role": "assistant", "content": "无法获取响应"})
            
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
