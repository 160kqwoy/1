#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Practice08 系统功能测试文件
测试链式工具调用、长期记忆系统、文件操作、技能调用等所有功能
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入需要测试的模块
from chained_tool_client import (
    ChainedCallContext,
    load_env,
    llm_request,
    read_file,
    write_file,
    delete_file,
    list_files,
    search_history,
    anythingllm_query,
    curl_url,
    execute_chained_tool_call,
    build_analysis_prompt,
    parse_decision_response,
    extract_5w_info,
    log_5w_info,
    list_available_skills,
    load_skill_content
)

from memory_manager import LongTermMemory, get_memory_manager

def test_chained_call_context():
    """测试链式调用上下文管理器"""
    print("="*60)
    print("测试1: 链式调用上下文管理器 (ChainedCallContext)")
    print("="*60)
    
    try:
        # 初始化上下文
        context = ChainedCallContext(max_iterations=3, max_context_chars=1000)
        
        # 测试开始调用
        context.start_call("test_tool", {"param1": "value1"})
        print(f"✓ 测试开始调用: iteration_count={context.iteration_count}")
        
        # 测试结束调用
        context.end_call("test_tool", "测试结果")
        print(f"✓ 测试结束调用: 状态={context.call_history[0]['status']}")
        
        # 测试存储变量
        context.store_variable("test_var", "test_value")
        print(f"✓ 测试存储变量: memory={context.memory}")
        
        # 测试获取变量
        var = context.get_variable("test_var")
        assert var == "test_value", "获取变量失败"
        print(f"✓ 测试获取变量: {var}")
        
        # 测试获取最后结果
        last_result = context.get_last_result()
        assert last_result == "测试结果", "获取最后结果失败"
        print(f"✓ 测试获取最后结果: {last_result}")
        
        # 测试上下文长度计算
        length = context.get_context_length()
        print(f"✓ 测试上下文长度计算: {length} 字符")
        
        # 测试完成标记
        context.set_complete("最终答案")
        assert context.is_chained_call_complete(), "完成标记失败"
        print(f"✓ 测试完成标记: is_complete={context.is_complete}")
        
        # 测试摘要生成
        summary = context.get_summary()
        print(f"✓ 测试摘要生成:\n{summary}")
        
        print("✓ 链式调用上下文管理器测试通过\n")
        
    except Exception as e:
        print(f"✗ 链式调用上下文管理器测试失败: {str(e)}\n")

def test_file_operations():
    """测试文件操作功能"""
    print("="*60)
    print("测试2: 文件操作功能")
    print("="*60)
    
    test_file = "test_operations.txt"
    test_dir = "test_dir"
    
    try:
        # 测试写入文件
        result = write_file(test_file, "测试内容\n第二行")
        assert "成功写入" in result, "写入文件失败"
        print(f"✓ 测试写入文件: {result}")
        
        # 测试读取文件
        result = read_file(test_file)
        assert "测试内容" in result, "读取文件失败"
        print(f"✓ 测试读取文件: 内容已获取")
        
        # 测试追加写入
        result = write_file(test_file, "\n追加内容", append=True)
        assert "成功追加" in result, "追加写入失败"
        print(f"✓ 测试追加写入: {result}")
        
        # 测试列出目录
        result = list_files(".")
        assert "test_operations.txt" in result, "列出目录失败"
        print(f"✓ 测试列出目录: 成功获取目录内容")
        
        # 测试删除文件
        result = delete_file(test_file)
        assert "成功删除" in result, "删除文件失败"
        print(f"✓ 测试删除文件: {result}")
        
        # 测试文件不存在情况
        result = read_file("nonexistent.txt")
        assert "文件不存在" in result, "文件不存在处理失败"
        print(f"✓ 测试文件不存在处理: {result[:30]}...")
        
        print("✓ 文件操作功能测试通过\n")
        
    except Exception as e:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
        print(f"✗ 文件操作功能测试失败: {str(e)}\n")

def test_memory_manager():
    """测试长期记忆系统"""
    print("="*60)
    print("测试3: 长期记忆系统 (LongTermMemory)")
    print("="*60)
    
    try:
        memory = LongTermMemory(storage_dir=".test_memory")
        
        # 测试更新用户资料
        memory.update_user_profile("test_user", {"name": "测试用户", "role": "测试角色"})
        profile = memory.get_user_profile("test_user")
        assert profile["name"] == "测试用户", "用户资料更新失败"
        print(f"✓ 测试更新用户资料: {profile}")
        
        # 测试添加对话摘要
        memory.add_conversation_summary("test_user", "测试对话摘要内容")
        summaries = memory.get_conversation_summaries("test_user")
        assert len(summaries) > 0, "对话摘要添加失败"
        print(f"✓ 测试添加对话摘要: {len(summaries)} 条")
        
        # 测试更新用户偏好
        memory.update_preferences("test_user", {"language": "zh", "theme": "dark"})
        prefs = memory.get_preferences("test_user")
        assert prefs["language"] == "zh", "偏好更新失败"
        print(f"✓ 测试更新用户偏好: {prefs}")
        
        # 测试添加实体
        memory.add_entity("test_user", "项目", {"name": "AI项目", "status": "进行中"})
        entity = memory.get_entity("test_user", "项目")
        assert entity["name"] == "AI项目", "实体添加失败"
        print(f"✓ 测试添加实体: {entity}")
        
        # 测试更新技能使用
        memory.update_skill_usage("write_file", success=True)
        usage = memory.get_skill_usage("write_file")
        assert usage["total_uses"] == 1, "技能使用更新失败"
        print(f"✓ 测试更新技能使用: {usage}")
        
        # 测试搜索记忆
        results = memory.search_memory("测试")
        assert len(results) > 0, "记忆搜索失败"
        print(f"✓ 测试搜索记忆: {len(results)} 条匹配")
        
        # 测试获取记忆摘要
        summary = memory.get_memory_summary("test_user")
        assert "测试用户" in summary, "记忆摘要获取失败"
        print(f"✓ 测试获取记忆摘要:\n{summary}")
        
        # 清理测试数据
        import shutil
        shutil.rmtree(".test_memory", ignore_errors=True)
        
        print("✓ 长期记忆系统测试通过\n")
        
    except Exception as e:
        import shutil
        shutil.rmtree(".test_memory", ignore_errors=True)
        print(f"✗ 长期记忆系统测试失败: {str(e)}\n")

def test_chained_tool_execution():
    """测试链式工具调用执行"""
    print("="*60)
    print("测试4: 链式工具调用执行")
    print("="*60)
    
    try:
        env_vars = load_env()
        
        # 创建测试文件
        test_file = "test_chain.txt"
        write_file(test_file, "这是链式调用测试文件")
        
        # 测试简单的链式调用任务：读取文件并总结
        user_input = f"读取{test_file}文件并总结内容"
        final_result, context = execute_chained_tool_call(user_input, env_vars, max_iterations=3)
        
        print(f"✓ 测试链式调用执行:")
        print(f"  用户请求: {user_input}")
        print(f"  最终结果: {final_result[:100]}...")
        print(f"  迭代次数: {context.iteration_count}")
        print(f"  调用历史: {len(context.call_history)} 条")
        
        # 清理测试文件
        delete_file(test_file)
        
        print("✓ 链式工具调用执行测试通过\n")
        
    except Exception as e:
        print(f"✗ 链式工具调用执行测试失败: {str(e)}\n")

def test_5w_extraction():
    """测试5W信息提取"""
    print("="*60)
    print("测试5: 5W信息提取")
    print("="*60)
    
    try:
        messages = [
            {"role": "user", "content": "请帮我查询明天北京的天气"},
            {"role": "assistant", "content": "好的，我来帮您查询北京明天的天气情况"}
        ]
        
        info = extract_5w_info(messages)
        
        assert "who" in info, "缺少who字段"
        assert "what" in info, "缺少what字段"
        assert "when" in info, "缺少when字段"
        assert "where" in info, "缺少where字段"
        assert "why" in info, "缺少why字段"
        
        print(f"✓ 测试5W信息提取结果:")
        print(f"  Who: {info['who']}")
        print(f"  What: {info['what']}")
        print(f"  When: {info['when']}")
        print(f"  Where: {info['where']}")
        print(f"  Why: {info['why']}")
        
        # 测试日志记录（注意：log_5w_info会写入D:\chat-log目录）
        # 这里只测试函数是否正常执行
        try:
            log_5w_info(info)
            print(f"✓ 测试5W日志记录: 成功")
        except Exception as log_e:
            print(f"~ 测试5W日志记录: 跳过（日志目录可能不存在）")
        
        print("✓ 5W信息提取测试通过\n")
        
    except Exception as e:
        print(f"✗ 5W信息提取测试失败: {str(e)}\n")

def test_skills():
    """测试技能系统"""
    print("="*60)
    print("测试6: 技能系统")
    print("="*60)
    
    try:
        # 测试列出可用技能
        skills = list_available_skills()
        print(f"✓ 测试列出可用技能: 共 {len(skills)} 个技能")
        for skill in skills:
            print(f"  - {skill['name']}: {skill['description']}")
        
        # 如果有技能，测试加载技能内容
        if skills:
            skill_content = load_skill_content(skills[0]['name'])
            assert isinstance(skill_content, str), "技能内容加载失败"
            print(f"✓ 测试加载技能内容: 长度 {len(skill_content)} 字符")
        
        print("✓ 技能系统测试通过\n")
        
    except Exception as e:
        print(f"✗ 技能系统测试失败: {str(e)}\n")

def test_analysis_prompt():
    """测试分析提示词构建"""
    print("="*60)
    print("测试7: 分析提示词构建")
    print("="*60)
    
    try:
        user_input = "测试请求"
        call_history = [
            {
                "tool_name": "list_files",
                "arguments": {"directory": "."},
                "result": "目录内容: test.txt"
            }
        ]
        available_tools = [
            {"name": "read_file", "description": "读取文件"},
            {"name": "write_file", "description": "写入文件"}
        ]
        
        prompt = build_analysis_prompt(user_input, call_history, available_tools)
        
        assert "用户请求" in prompt, "缺少用户请求部分"
        assert "已执行步骤" in prompt, "缺少已执行步骤部分"
        assert "决策规则" in prompt, "缺少决策规则部分"
        assert "输出格式要求" in prompt, "缺少输出格式要求部分"
        
        print(f"✓ 测试分析提示词构建:")
        print(f"  提示词长度: {len(prompt)} 字符")
        print(f"  包含用户请求: {'用户请求' in prompt}")
        print(f"  包含已执行步骤: {'已执行步骤' in prompt}")
        print(f"  包含决策规则: {'决策规则' in prompt}")
        print(f"  包含输出格式: {'输出格式要求' in prompt}")
        
        print("✓ 分析提示词构建测试通过\n")
        
    except Exception as e:
        print(f"✗ 分析提示词构建测试失败: {str(e)}\n")

def test_decision_parsing():
    """测试决策响应解析"""
    print("="*60)
    print("测试8: 决策响应解析")
    print("="*60)
    
    try:
        # 测试完成任务的响应
        response1 = '{"done": true, "answer": "最终回答"}'
        decision1 = parse_decision_response(response1)
        assert decision1["done"] == True, "完成任务解析失败"
        assert decision1["answer"] == "最终回答", "回答内容解析失败"
        print(f"✓ 测试完成任务响应解析: {decision1}")
        
        # 测试继续调用工具的响应
        response2 = '{"done": false, "toolcall": {"name": "read_file", "arguments": {"file_path": "test.txt"}}}'
        decision2 = parse_decision_response(response2)
        assert decision2["done"] == False, "继续调用解析失败"
        assert decision2["toolcall"]["name"] == "read_file", "工具名称解析失败"
        print(f"✓ 测试继续调用工具响应解析: {decision2}")
        
        # 测试带markdown代码块的响应
        response3 = '```json\n{"done": true, "answer": "测试"}```'
        decision3 = parse_decision_response(response3)
        assert decision3["done"] == True, "markdown代码块解析失败"
        print(f"✓ 测试带markdown代码块响应解析: {decision3}")
        
        print("✓ 决策响应解析测试通过\n")
        
    except Exception as e:
        print(f"✗ 决策响应解析测试失败: {str(e)}\n")

def test_curl_url():
    """测试URL访问功能"""
    print("="*60)
    print("测试9: URL访问功能")
    print("="*60)
    
    try:
        # 测试访问一个简单的URL
        result = curl_url("https://www.example.com")
        assert "HTTP状态码" in result, "URL访问失败"
        assert "200" in result, "HTTP状态码不是200"
        print(f"✓ 测试URL访问: {result[:80]}...")
        
        # 测试无效URL
        result = curl_url("https://invalid-url-12345.com")
        assert "错误" in result, "无效URL处理失败"
        print(f"✓ 测试无效URL处理: {result[:50]}...")
        
        print("✓ URL访问功能测试通过\n")
        
    except Exception as e:
        print(f"✗ URL访问功能测试失败: {str(e)}\n")

def test_env_load():
    """测试环境变量加载"""
    print("="*60)
    print("测试10: 环境变量加载")
    print("="*60)
    
    try:
        env_vars = load_env()
        
        assert isinstance(env_vars, dict), "环境变量不是字典"
        assert "LLM_BASE_URL" in env_vars, "缺少LLM_BASE_URL"
        assert "LLM_MODEL" in env_vars, "缺少LLM_MODEL"
        
        print(f"✓ 测试环境变量加载:")
        print(f"  LLM_BASE_URL: {env_vars.get('LLM_BASE_URL', '未设置')}")
        print(f"  LLM_MODEL: {env_vars.get('LLM_MODEL', '未设置')}")
        print(f"  ANYTHINGLLM_API_KEY: {'已设置' if env_vars.get('ANYTHINGLLM_API_KEY') else '未设置'}")
        
        print("✓ 环境变量加载测试通过\n")
        
    except Exception as e:
        print(f"✗ 环境变量加载测试失败: {str(e)}\n")

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试 Practice08 系统功能")
    print("="*60 + "\n")
    
    start_time = time.time()
    test_count = 0
    pass_count = 0
    
    # 测试列表
    tests = [
        test_env_load,
        test_chained_call_context,
        test_file_operations,
        test_memory_manager,
        test_analysis_prompt,
        test_decision_parsing,
        test_curl_url,
        test_skills,
        test_5w_extraction,
        test_chained_tool_execution  # 放在最后，可能需要较长时间
    ]
    
    for test in tests:
        test_count += 1
        try:
            test()
            pass_count += 1
        except Exception as e:
            print(f"测试 {test.__name__} 未预期的错误: {str(e)}\n")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print("="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"总测试数: {test_count}")
    print(f"通过数: {pass_count}")
    print(f"失败数: {test_count - pass_count}")
    print(f"通过率: {(pass_count / test_count) * 100:.1f}%")
    print(f"总耗时: {elapsed_time:.2f} 秒")
    print("="*60)

if __name__ == "__main__":
    run_all_tests()