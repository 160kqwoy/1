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

## 注意事项

- 请确保`.env`文件中的API密钥安全，不要提交到版本控制
- 根据实际使用的LLM服务调整配置参数
- 流式输出需要服务端支持stream模式
- 天气查询功能依赖外部服务(wttr.in)，需要网络连接