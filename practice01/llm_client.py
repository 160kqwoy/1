import os
import json
import time
import http.client
from urllib.parse import urlparse


def load_env():
    """加载.env文件中的环境变量"""
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
    
    # 验证必要的环境变量
    required_vars = ['LLM_BASE_URL', 'LLM_MODEL', 'LLM_API_KEY']
    for var in required_vars:
        if var not in env_vars:
            print(f"错误: 缺少必要的环境变量 {var}")
            return None
    
    return env_vars


def call_llm(env_vars, prompt):
    """调用LLM API并返回响应和统计信息"""
    # 解析BASE_URL
    parsed_url = urlparse(env_vars['LLM_BASE_URL'])
    host = parsed_url.netloc
    path = parsed_url.path or '/'
    if not path.endswith('/'):
        path += '/'
    path += 'chat/completions'
    
    # 准备请求数据
    data = {
        "model": env_vars.get('LLM_MODEL', 'gpt-3.5-turbo'),
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": int(env_vars.get('LLM_MAX_TOKENS', 1000)),
        "temperature": float(env_vars.get('LLM_TEMPERATURE', 0.7))
    }
    
    # 准备请求头
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {env_vars['LLM_API_KEY']}"
    }
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 根据协议选择连接类型
        if parsed_url.scheme == 'https':
            conn = http.client.HTTPSConnection(host)
        else:
            conn = http.client.HTTPConnection(host)
        
        # 发送请求
        conn.request('POST', path, json.dumps(data), headers)
        
        # 获取响应
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
        conn.close()
        

        
        # 解析响应
        response_json = json.loads(response_data)
        
        # 计算耗时
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 检查是否有错误
        if 'error' in response_json:
            print(f"API错误: {response_json['error']}")
            return {
                'content': '',
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0,
                'elapsed_time': elapsed_time,
                'tokens_per_second': 0,
                'error': response_json['error']
            }
        
        # 提取token使用情况
        usage = response_json.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        # 计算token/速度
        tokens_per_second = total_tokens / elapsed_time if elapsed_time > 0 else 0
        
        # 提取响应内容
        content = ""
        if 'choices' in response_json and response_json['choices']:
            content = response_json['choices'][0].get('message', {}).get('content', "")
        
        # 返回结果
        return {
            'content': content,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'elapsed_time': elapsed_time,
            'tokens_per_second': tokens_per_second
        }
        
    except Exception as e:
        print(f"错误: {str(e)}")
        return None


def main():
    """主函数"""
    # 加载环境变量
    env_vars = load_env()
    if not env_vars:
        return
    
    # 测试提示词
    prompt = "请解释什么是人工智能，用简单易懂的语言"
    
    print("正在调用LLM...")
    result = call_llm(env_vars, prompt)
    
    if result:
        if 'error' in result:
            print(f"\n=== 调用失败 ===")
            print(f"错误信息: {result['error']}")
        else:
            print("\n=== 响应内容 ===")
            print(result['content'])
            print("\n=== 统计信息 ===")
            print(f"提示词token: {result['prompt_tokens']}")
            print(f"完成token: {result['completion_tokens']}")
            print(f"总token: {result['total_tokens']}")
            print(f"耗时: {result['elapsed_time']:.2f} 秒")
            print(f"速度: {result['tokens_per_second']:.2f} token/秒")
    else:
        print("调用LLM失败")


if __name__ == "__main__":
    main()