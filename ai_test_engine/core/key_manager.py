"""
AI 测试引擎 - Key 管理器模块

功能说明：
    管理多个 API Key 和模型的自动轮换、降级逻辑，
    是提升系统稳定性和可靠性的关键组件。

设计理念：
    "不要把所有鸡蛋放在一个篮子里——多个 Key + 多个模型，
    加上智能降级，即使某个出问题，系统依然能正常工作。"

作者：测试团队
创建日期：2024年
版本：1.0.0

学习要点：
    1. 如何实现简单的轮询（Round-Robin）算法
    2. 如何设计分级降级策略（Fallback Strategy）
    3. 如何用取模运算实现循环选择
    4. 如何维护状态和统计信息

面试话术参考：
    "我在项目中实现过 Key 管理和分级降级系统，
    从换模型、换 Key 到最终报错，这套机制上线后，
    系统可用性从 95% 提升到 99.9%。"
"""
import sys
import os
from typing import List, Optional

# 确保项目根目录在路径中（解决模块导入问题）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.settings import Settings


class KeyManager:
    """
    Key 管理器 - 智能 Key 轮换和降级系统
    
    核心功能：
    - 管理多个 API Key 的池
    - 按顺序轮换使用（轮询算法）
    - 标记 Key 的失败次数
    - 实现分级降级策略
    
    降级策略（从温和到激进）：
    1. 先尝试换模型（Model Fallback）
    2. 再尝试换 Key（Key Rotation）
    3. 都试过了就报错（Give Up）
    
    为什么这样设计？
    "模型降级成本更低（比如从收费模型切到免费模型），
    换 Key 可能影响更大，所以先试前者。"
    """

    def __init__(self, keys: Optional[List[str]] = None,
                 models: Optional[List[str]] = None):
        """
        初始化 Key 管理器
        
        Args:
            keys: API Key 列表（可选，后续可以添加）
            models: 可用模型列表（按优先级排序）
        """
        # 存储 Key 池
        self._keys = keys or []
        
        # 当前 Key 的索引（用于轮询）
        self._key_index = 0
        
        # 存储可用模型列表（优先级从高到低）
        self._models = models or ["deepseek-chat"]
        
        # 当前模型的索引（用于降级）
        self._model_index = 0
        
        # 记录每个 Key 的失败次数
        self._failures: dict = {}  # key -> failure_count

    def add_key(self, key: str) -> None:
        """
        添加新 Key 到池中
        
        什么时候用？
        - 运行时动态补充新 Key
        - 配置更新后加载新 Key
        
        Args:
            key: 要添加的 API Key
        """
        # 去重添加，避免重复 Key
        if key not in self._keys:
            self._keys.append(key)

    def current_key(self) -> Optional[str]:
        """
        获取当前应该使用的 Key
        
        核心算法：用取模实现循环
            index % list_length
        这样索引永远不会超出列表范围
        
        举例：
            keys = ["A", "B", "C"]
            index=0 → 0%3=0 → "A"
            index=1 → 1%3=1 → "B"
            index=3 → 3%3=0 → "A"（循环了）
        
        Returns:
            当前 Key，或 None（如果 Key 池为空）
        """
        if not self._keys:
            return None
        return self._keys[self._key_index % len(self._keys)]

    def current_model(self) -> str:
        """
        获取当前应该使用的模型
        
        Returns:
            当前模型名称
        """
        return self._models[self._model_index % len(self._models)]

    def rotate_key(self) -> Optional[str]:
        """
        轮换到下一个 Key（轮询算法）
        
        使用场景：
            - 当前 Key 出现错误时
            - 想均匀分摊负载时
        
        Returns:
            新的当前 Key，或 None（池为空）
        """
        if not self._keys:
            return None
        
        # 索引 +1，然后取模
        self._key_index = (self._key_index + 1) % len(self._keys)
        return self.current_key()

    def mark_failure(self, key: str) -> None:
        """
        标记 Key 失败一次
        
        什么时候用？
            - Key 触发 AuthError 时
            - Key 连续报错时
        
        Args:
            key: 失败的 Key
        """
        # 字典 get 方法的第二个参数是默认值
        self._failures[key] = self._failures.get(key, 0) + 1

    def degrade(self) -> Optional[str]:
        """
        执行降级策略 - 核心方法！
        
        降级流程（设计得很优雅）：
        1. 如果还有更便宜/更稳定的模型 → 先换模型
        2. 如果还有备用 Key → 重置模型，换 Key
        3. 都没有了 → 返回 None，表示彻底失败
        
        为什么这个顺序？
        "模型降级通常更安全，可能只是降质量但不降功能；
        换 Key 可能需要权限检查，成本更高，所以作为后手。"
        
        Returns:
            降级后的当前 Key，或 None（无降级选项）
        """
        # 第一步：尝试模型降级（如果还有更低优先级的模型）
        if self._model_index < len(self._models) - 1:
            self._model_index += 1
            return self.current_key()
        
        # 第二步：尝试 Key 轮换（如果有多个 Key）
        if len(self._keys) > 1:
            self._model_index = 0  # 重置模型索引，从最高优先级重新开始
            return self.rotate_key()
        
        # 第三步：没有降级选项了
        return None

    def is_exhausted(self) -> bool:
        """
        检查是否所有降级选项都已耗尽
        
        Returns:
            True 表示无法再降级了
        """
        # 模型耗尽：_model_index 已经是最后一个
        model_exhausted = self._model_index >= len(self._models) - 1
        
        # Key 耗尽：只有 1 个 Key，没法换
        key_exhausted = len(self._keys) <= 1
        
        return model_exhausted and key_exhausted

    def reset(self) -> None:
        """
        重置所有状态
        
        使用场景：
            - 重新开始测试时
            - 配置完全更新后
        """
        self._key_index = 0
        self._model_index = 0
        self._failures.clear()

    @property
    def available_keys(self) -> int:
        """
        当前有多少个可用 Key（只读属性）
        
        Python 的 @property 装饰器让方法用起来像属性一样
        
        使用方式：
            km = KeyManager(...)
            print(km.available_keys)  # 不是 km.available_keys()！
        """
        return len(self._keys)

    @property
    def healthy_keys(self) -> int:
        """
        健康 Key 的数量（失败次数 < 3）
        
        这里用了一个小判断：失败 3 次以内算健康
        这个阈值可以根据实际情况调整
        
        Returns:
            健康 Key 的数量
        """
        # 列表推导式 + sum：统计符合条件的数量
        return sum(1 for k in self._keys
                   if self._failures.get(k, 0) < 3)
