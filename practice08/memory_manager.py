import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

class LongTermMemory:
    """
    长期记忆系统，用于跨会话存储和检索用户信息、对话历史和偏好
    
    记忆结构：
    - 用户基本信息 (user_profile)
    - 对话历史摘要 (conversation_summaries)
    - 用户偏好 (preferences)
    - 重要实体 (entities)
    - 技能使用记录 (skill_usage)
    """
    
    def __init__(self, storage_dir: str = ".memory"):
        """
        初始化长期记忆系统
        
        Args:
            storage_dir: 记忆存储目录，默认为.memory
        """
        self.storage_dir = storage_dir
        self.memory_file = os.path.join(storage_dir, "memory.json")
        self._initialize_storage()
        
    def _initialize_storage(self):
        """初始化存储目录"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        
        if not os.path.exists(self.memory_file):
            self._save_memory(self._create_empty_memory())
    
    def _create_empty_memory(self) -> dict:
        """创建空的记忆结构"""
        return {
            "user_profile": {},
            "conversation_summaries": [],
            "preferences": {},
            "entities": {},
            "skill_usage": {},
            "last_access": datetime.now().isoformat()
        }
    
    def _load_memory(self) -> dict:
        """加载记忆数据"""
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._create_empty_memory()
    
    def _save_memory(self, memory: dict):
        """保存记忆数据"""
        memory["last_access"] = datetime.now().isoformat()
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    
    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]):
        """
        更新用户资料
        
        Args:
            user_id: 用户标识符
            profile_data: 用户资料数据
        """
        memory = self._load_memory()
        
        if user_id not in memory["user_profile"]:
            memory["user_profile"][user_id] = {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "data": {}
            }
        
        memory["user_profile"][user_id]["data"].update(profile_data)
        memory["user_profile"][user_id]["updated_at"] = datetime.now().isoformat()
        
        self._save_memory(memory)
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户资料
        
        Args:
            user_id: 用户标识符
        
        Returns:
            用户资料字典，如果不存在返回None
        """
        memory = self._load_memory()
        profile = memory["user_profile"].get(user_id)
        return profile["data"] if profile else None
    
    def add_conversation_summary(self, user_id: str, summary: str, timestamp: Optional[str] = None):
        """
        添加对话历史摘要
        
        Args:
            user_id: 用户标识符
            summary: 对话摘要
            timestamp: 时间戳，默认为当前时间
        """
        memory = self._load_memory()
        
        entry = {
            "timestamp": timestamp or datetime.now().isoformat(),
            "user_id": user_id,
            "summary": summary
        }
        
        memory["conversation_summaries"].append(entry)
        
        # 保留最近100条对话摘要
        if len(memory["conversation_summaries"]) > 100:
            memory["conversation_summaries"] = memory["conversation_summaries"][-100:]
        
        self._save_memory(memory)
    
    def get_conversation_summaries(self, user_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取对话历史摘要
        
        Args:
            user_id: 用户标识符，可选，不指定则返回所有
            limit: 返回数量限制，默认10条
        
        Returns:
            对话摘要列表
        """
        memory = self._load_memory()
        
        summaries = memory["conversation_summaries"]
        
        if user_id:
            summaries = [s for s in summaries if s["user_id"] == user_id]
        
        return summaries[-limit:]
    
    def update_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """
        更新用户偏好
        
        Args:
            user_id: 用户标识符
            preferences: 用户偏好字典
        """
        memory = self._load_memory()
        
        if user_id not in memory["preferences"]:
            memory["preferences"][user_id] = {}
        
        memory["preferences"][user_id].update(preferences)
        
        self._save_memory(memory)
    
    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户偏好
        
        Args:
            user_id: 用户标识符
        
        Returns:
            用户偏好字典
        """
        memory = self._load_memory()
        return memory["preferences"].get(user_id, {})
    
    def add_entity(self, user_id: str, entity_name: str, entity_data: Dict[str, Any]):
        """
        添加重要实体
        
        Args:
            user_id: 用户标识符
            entity_name: 实体名称
            entity_data: 实体数据
        """
        memory = self._load_memory()
        
        if user_id not in memory["entities"]:
            memory["entities"][user_id] = {}
        
        memory["entities"][user_id][entity_name] = {
            "data": entity_data,
            "updated_at": datetime.now().isoformat()
        }
        
        self._save_memory(memory)
    
    def get_entity(self, user_id: str, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        获取实体信息
        
        Args:
            user_id: 用户标识符
            entity_name: 实体名称
        
        Returns:
            实体数据，如果不存在返回None
        """
        memory = self._load_memory()
        entities = memory["entities"].get(user_id, {})
        entity = entities.get(entity_name)
        return entity["data"] if entity else None
    
    def update_skill_usage(self, skill_name: str, success: bool = True):
        """
        更新技能使用记录
        
        Args:
            skill_name: 技能名称
            success: 是否成功执行
        """
        memory = self._load_memory()
        
        if skill_name not in memory["skill_usage"]:
            memory["skill_usage"][skill_name] = {
                "total_uses": 0,
                "success_count": 0,
                "last_used": None
            }
        
        memory["skill_usage"][skill_name]["total_uses"] += 1
        if success:
            memory["skill_usage"][skill_name]["success_count"] += 1
        memory["skill_usage"][skill_name]["last_used"] = datetime.now().isoformat()
        
        self._save_memory(memory)
    
    def get_skill_usage(self, skill_name: str = None) -> Dict[str, Any]:
        """
        获取技能使用统计
        
        Args:
            skill_name: 技能名称，可选，不指定则返回所有
        
        Returns:
            技能使用统计字典
        """
        memory = self._load_memory()
        
        if skill_name:
            return memory["skill_usage"].get(skill_name, {})
        return memory["skill_usage"]
    
    def search_memory(self, query: str, user_id: str = None) -> List[Dict[str, Any]]:
        """
        搜索记忆中的相关内容
        
        Args:
            query: 搜索关键词
            user_id: 用户标识符，可选
        
        Returns:
            匹配的记忆条目列表
        """
        memory = self._load_memory()
        results = []
        
        # 搜索对话摘要
        for summary in memory["conversation_summaries"]:
            if user_id and summary["user_id"] != user_id:
                continue
            if query.lower() in summary["summary"].lower():
                results.append({
                    "type": "conversation",
                    "timestamp": summary["timestamp"],
                    "content": summary["summary"]
                })
        
        # 搜索用户资料
        for uid, profile in memory["user_profile"].items():
            if user_id and uid != user_id:
                continue
            profile_str = json.dumps(profile["data"], ensure_ascii=False)
            if query.lower() in profile_str.lower():
                results.append({
                    "type": "profile",
                    "user_id": uid,
                    "content": profile["data"]
                })
        
        # 搜索实体
        for uid, entities in memory["entities"].items():
            if user_id and uid != user_id:
                continue
            for name, entity in entities.items():
                entity_str = json.dumps(entity["data"], ensure_ascii=False)
                if query.lower() in entity_str.lower() or query.lower() in name.lower():
                    results.append({
                        "type": "entity",
                        "user_id": uid,
                        "entity_name": name,
                        "content": entity["data"]
                    })
        
        return sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def get_memory_summary(self, user_id: str) -> str:
        """
        获取用户记忆摘要
        
        Args:
            user_id: 用户标识符
        
        Returns:
            记忆摘要字符串
        """
        profile = self.get_user_profile(user_id)
        summaries = self.get_conversation_summaries(user_id, limit=5)
        preferences = self.get_preferences(user_id)
        entities = self._load_memory()["entities"].get(user_id, {})
        
        summary = f"用户记忆摘要 (ID: {user_id})\n"
        summary += "="*40 + "\n"
        
        if profile:
            summary += f"用户资料: {json.dumps(profile, ensure_ascii=False)}\n\n"
        
        if summaries:
            summary += "最近对话:\n"
            for i, s in enumerate(summaries, 1):
                time_str = s["timestamp"].replace("T", " ")[:19]
                summary += f"  {i}. [{time_str}] {s['summary'][:50]}...\n"
            summary += "\n"
        
        if preferences:
            summary += f"用户偏好: {json.dumps(preferences, ensure_ascii=False)}\n\n"
        
        if entities:
            summary += f"已知实体: {', '.join(entities.keys())}\n"
        
        return summary

# 全局记忆管理器实例
_global_memory = None

def get_memory_manager() -> LongTermMemory:
    """获取全局记忆管理器实例"""
    global _global_memory
    if _global_memory is None:
        _global_memory = LongTermMemory()
    return _global_memory

if __name__ == "__main__":
    # 测试记忆系统
    memory = LongTermMemory()
    
    # 添加测试数据
    memory.update_user_profile("test_user", {
        "name": "张三",
        "company": "成都东软学院",
        "role": "学生"
    })
    
    memory.add_conversation_summary("test_user", "用户询问如何访问网页并总结内容")
    memory.update_preferences("test_user", {"language": "zh", "theme": "dark"})
    memory.add_entity("test_user", "项目", {"name": "AI智能体开发", "status": "进行中"})
    memory.update_skill_usage("write_file", success=True)
    
    # 测试检索
    print("用户资料:", memory.get_user_profile("test_user"))
    print("\n对话摘要:", memory.get_conversation_summaries("test_user"))
    print("\n用户偏好:", memory.get_preferences("test_user"))
    print("\n实体信息:", memory.get_entity("test_user", "项目"))
    print("\n技能使用:", memory.get_skill_usage("write_file"))
    print("\n搜索结果:", memory.search_memory("网页"))
    print("\n记忆摘要:\n", memory.get_memory_summary("test_user"))