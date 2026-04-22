# AI智能体开发教学项目

这是一个基于Python的AI智能体开发教学项目，包含多个递进式实践练习模块，从基础LLM调用到高级工具调用能力。

## 环境要求

- Python 3.12+
- 支持OpenAI兼容协议的LLM服务（如Qwen、Llama、ChatGLM等）

## 项目结构

```
.
├── .env              # 环境配置文件（需要手动创建）
├── .env.example      # 环境配置模板
├── .gitignore        # Git排除文件
├── venv/             # 虚拟环境
├── practice01/       # 练习1：基础LLM调用
│   └── llm_client.py
├── practice02/       # 练习2：流式聊天客户端
│   └── chat_client.py
├── practice03/       # 练习3：工具调用客户端
│   └── tool_chat_client.py
├── practice04/       # 练习4：聊天总结客户端
│   └── chat_summarize_client.py
├── practice05/       # 练习5：聊天日志客户端
│   └── chat_log_client.py
├── practice06/       # 练习6：AnythingLLM查询客户端
│   └── chat_anythingllm_client.py
└── README.md         # 项目说明
```

## 快速开始

### 1. 创建虚拟环境

```bash
D:\py3.12\python.exe -m venv venv
```

### 2. 激活虚拟环境

**Windows:**
```bash
venv\Scripts\activate
```

### 3. 配置环境变量

复制`env.example`为`.env`并填写正确的LLM配置：

```bash
copy env.example .env
```

编辑`.env`文件：

```env
# LLM配置
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_MODEL=your_model_name
LLM_API_KEY=your_api_key

# 其他配置
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7
```

## 练习模块

### Practice 01: 基础LLM调用

简单的LLM调用示例，支持token统计和性能监控。

**运行:**
```bash
python practice01/llm_client.py
```

### Practice 02: 流式聊天客户端

支持终端界面输入、流式输出、历史聊天记录自动添加上下文。

**运行:**
```bash
python practice02/chat_client.py
```

**功能特点:**
- 终端交互式聊天界面
- 流式输出，逐字显示回复
- 自动维护历史聊天记录
- 实时token统计和性能监控
- 按Ctrl+C退出

### Practice 03: 工具调用客户端

支持LLM调用工具来执行文件系统操作和网络访问，包括列出文件、重命名、删除、创建、读取文件和HTTP网页访问。

**运行:**
```bash
python practice03/tool_chat_client.py
```

**功能特点:**
- 终端交互式聊天界面
- 支持7种工具调用：
  - `list_files(directory)` - 列出目录下的文件信息
  - `rename_file(old_path, new_name)` - 重命名文件
  - `delete_file(file_path)` - 删除文件
  - `create_file(directory, filename, content)` - 创建文件并写入内容
  - `read_file(file_path)` - 读取文件内容
  - `curl_url(url)` - 通过HTTP/HTTPS访问指定URL并返回网页内容
  - `get_weather(city)` - 查询指定城市的天气信息
- 工具描述作为系统提示词发送给LLM
- 自动解析并执行工具调用
- 将工具执行结果反馈给LLM进行后续处理
- 实时token统计和性能监控
- 按Ctrl+C退出

### Practice 04: 聊天总结客户端

基于practice03扩展，实现聊天历史记录自动总结和压缩功能，优化长对话的上下文管理。

**运行:**
```bash
python practice04/chat_summarize_client.py
```

**功能特点:**
- 继承practice03的所有工具调用能力
- **自动总结触发条件:**
  - 对话轮数超过5轮
  - 上下文长度超过3000字符
- **总结策略:**
  - 对前70%左右的历史内容进行压缩总结
  - 保留最后30%左右的内容原文
  - 将总结结果插入历史记录顶部
- 支持工具调用（list_files, rename_file, delete_file, create_file, read_file, curl_url, get_weather）
- 实时显示总结进度和统计信息
- 实时token统计和性能监控
- 按Ctrl+C退出

**总结机制:**
1. 检测聊天历史是否达到触发条件
2. 计算需要保留的内容（约30%）和需要总结的内容（约70%）
3. 调用LLM对需要总结的部分进行压缩
4. 将总结结果替换原始历史的前半部分
5. 保留最近的对话内容保持上下文连贯性

### Practice 05: 聊天日志客户端

基于practice04扩展，实现5W关键信息提取和聊天历史搜索功能。

**运行:**
```bash
python practice05/chat_log_client.py
```

**功能特点:**
- **5W关键信息提取:**
  - 每5轮对话自动触发
  - 提取Who（谁）、What（做了什么）、When（时间）、Where（地点）、Why（原因）
  - 自动记录到 `D:\chat-log\log.txt` 文件
- **聊天历史搜索:**
  - 使用 `/search 关键词` 触发搜索
  - 识别"查找聊天历史"等自然语言表达
  - 将历史记录与用户请求结合进行分析
- 增量日志更新，自动创建目录和文件
- 实时token统计和性能监控
- 按Ctrl+C退出

**日志格式:**
```
==================================================
时间: 2024-01-15 10:30:00
Who（谁）: 用户与助手
What（做了什么）: 讨论天空颜色及科学原理
When（什么时候）: 
Where（在哪里）: 
Why（为什么）: 用户想了解天空呈蓝色的原因
--- 对话内容 ---
用户: 天空为什么是蓝色的
助手: 天空呈现蓝色主要是因为瑞利散射...
用户: 能详细解释一下吗
助手: 当然可以，瑞利散射是指...
==================================================
```

### Practice 06: AnythingLLM查询客户端

基于practice05扩展，添加使用curl调用AnythingLLM知识库API的功能。

**运行:**
```bash
python practice06/chat_anythingllm_client.py
```

**功能特点:**
- **继承practice05的所有功能**：5W信息提取、聊天历史搜索、日志记录
- **新增AnythingLLM查询工具:**
  - 使用subprocess模块调用curl命令
  - 访问 `http://localhost:3001/api/v1/workspace/{workspace}/chat` 接口
  - 使用message字段发送查询
  - 支持API密钥认证（Bearer Token）
  - 支持工作区名称配置
- **工具调用:** `anythingllm_query(message)` - 向AnythingLLM知识库查询数据
- **工作区管理:** `/workspaces` 命令 - 列出所有可用工作区
- 完善的错误处理，支持中文错误提示
- 自动处理API响应，提取textResponse字段

**配置说明:**
在 `.env` 文件中添加以下配置：
```env
ANYTHINGLLM_API_KEY=your_api_key_here
ANYTHINGLLM_WORKSPACE=ai
```

**可用命令:**
- `/search 关键词` - 搜索聊天历史记录
- `/workspaces` - 列出所有可用的AnythingLLM工作区

**文件操作工具:**
- `read_file(file_path)` - 读取指定文件的内容
- `write_file(file_path, content, append=False)` - 将内容写入指定文件
- `delete_file(file_path)` - 删除指定文件
- `list_files(directory)` - 列出指定目录中的文件和子目录

**使用示例:**
```
你: 查询知识库中关于AI的内容
AI: <function_calls>{"name":"anythingllm_query","arguments":{"message":"关于AI的内容"}}</function_calls>
--- 检测到工具调用 ---
工具名称: anythingllm_query
参数: {"message": "关于AI的内容"}
[系统] 执行curl命令: curl -X POST http://localhost:3001/api/v1/workspace/ai/chat ...
工具执行结果:

人工智能（AI）是一种使机器能够模拟人类智能的技术和学科...
```

**API响应格式:**
```json
{
  "id": "xxx",
  "type": "textResponse",
  "sources": [],
  "close": true,
  "error": null,
  "textResponse": "知识库返回的内容..."
}
```

## 使用说明

1. 确保LLM服务已启动并加载了模型
2. 正确配置`.env`文件中的连接信息
3. 激活虚拟环境后运行相应的练习脚本

## 退出方式

按 `Ctrl+C` 退出聊天客户端，会显示会话统计信息。

## 项目特性

- **纯Python实现**：不依赖第三方LLM SDK，直接使用http.client进行API调用
- **渐进式学习**：从基础调用到工具调用，逐步提升AI智能体开发能力
- **实时监控**：每个模块都包含token统计、耗时计算、处理速度等性能指标
- **优雅退出**：支持Ctrl+C退出并显示完整的会话统计信息
- **工具扩展**：Practice 03支持灵活的工具扩展机制

## 学习路径

1. **Practice 01**：学习基础LLM API调用方式，理解请求/响应结构
2. **Practice 02**：掌握流式输出和上下文管理，构建交互式聊天
3. **Practice 03**：学习工具调用机制，实现AI智能体的外部能力扩展
4. **Practice 04**：学习对话总结和上下文压缩技术，优化长对话管理
5. **Practice 05**：学习5W信息提取和聊天历史搜索，实现对话日志记录与检索
6. **Practice 06**：学习使用subprocess调用外部命令，实现与AnythingLLM知识库的集成

## 注意事项

- 请确保`.env`文件中的API密钥安全，不要提交到版本控制
- 根据实际使用的LLM服务调整配置参数
- 流式输出需要服务端支持stream模式
- 天气查询功能依赖外部服务(wttr.in)，需要网络连接