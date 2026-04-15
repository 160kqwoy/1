# AI智能体开发教学项目

这是一个基于Python的AI智能体开发教学项目，包含多个实践练习模块。

## 环境要求

- Python 3.12+
- 支持OpenAI兼容协议的LLM服务

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

## 使用说明

1. 确保LLM服务已启动并加载了模型
2. 正确配置`.env`文件中的连接信息
3. 激活虚拟环境后运行相应的练习脚本

## 退出方式

按 `Ctrl+C` 退出聊天客户端，会显示会话统计信息。

## 注意事项

- 请确保`.env`文件中的API密钥安全，不要提交到版本控制
- 根据实际使用的LLM服务调整配置参数
- 流式输出需要服务端支持stream模式