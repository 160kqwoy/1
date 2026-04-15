import os
import json
import time
import sys
import http.client
from urllib.parse import urlparse


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


def stream_llm_response(env_vars, messages):
    parsed_url = urlparse(env_vars['LLM_BASE_URL'])
    host = parsed_url.hostname or parsed_url.netloc
    path = parsed_url.path or '/'
    if not path.endswith('/'):
        path += '/'
    path += 'chat/completions'
    
    data = json.dumps({
        "model": env_vars.get('LLM_MODEL', 'gpt-3.5-turbo'),
        "messages": messages,
        "max_tokens": int(env_vars.get('LLM_MAX_TOKENS', 1000)),
        "temperature": float(env_vars.get('LLM_TEMPERATURE', 0.7)),
        "stream": True
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {env_vars['LLM_API_KEY']}"
    }
    
    port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
    
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
        output_buffer = ''
        
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
                            if output_buffer:
                                sys.stdout.write(output_buffer)
                                sys.stdout.flush()
                                full_content += output_buffer
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
        
        if output_buffer:
            sys.stdout.write(output_buffer)
            sys.stdout.flush()
            full_content += output_buffer
        
        conn.close()
        
        print(f"\n调试: full_content长度={len(full_content)}, completion_tokens={completion_tokens}, prompt_tokens={prompt_tokens}")
        
        if completion_tokens == 0 and full_content:
            print("调试: 正在估算completion_tokens")
            completion_tokens = len(full_content) // 4
        
        if prompt_tokens == 0:
            print("调试: 正在估算prompt_tokens")
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


def main():
    env_vars = load_env()
    if not env_vars:
        return
    
    print("=== LLM聊天客户端 ===")
    print("输入消息开始聊天，按 Ctrl+C 退出")
    print("=" * 40)
    
    history = []
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
                
                if usage:
                    total_prompt_tokens += usage['prompt_tokens']
                    total_completion_tokens += usage['completion_tokens']
                    
                    elapsed_time = time.time() - start_time
                    total_tokens = total_prompt_tokens + total_completion_tokens
                    tokens_per_second = total_tokens / elapsed_time if elapsed_time > 0 else 0
                    
                    print(f"\n[统计] 提示词: {usage['prompt_tokens']} | 回复: {usage['completion_tokens']} | "
                          f"累计: {total_tokens} | 速度: {tokens_per_second:.2f} token/s")
            
            print("-" * 40)
    
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