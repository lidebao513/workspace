"""
Day 27 — Key 管理器

负责 API Key 轮换和降级策略。
"""
import sys
import os
from typing import List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.settings import Settings


class KeyManager:
    """Key 管理器

    持有一个 Key 池，按顺序使用。当前 Key 失效时自动切换到下一个。
    支持两种降级策略：换模型 → 换 Key → 报错。

    Args:
        keys: API Key 列表
        models: 可用的模型列表（按优先级排序）
    """

    def __init__(self, keys: Optional[List[str]] = None,
                 models: Optional[List[str]] = None):
        self._keys = keys or []
        self._key_index = 0
        self._models = models or ["deepseek-chat"]
        self._model_index = 0
        self._failures: dict = {}  # key -> failure_count

    def add_key(self, key: str) -> None:
        """添加 Key"""
        if key not in self._keys:
            self._keys.append(key)

    def current_key(self) -> Optional[str]:
        """获取当前 Key"""
        if not self._keys:
            return None
        return self._keys[self._key_index % len(self._keys)]

    def current_model(self) -> str:
        """获取当前模型"""
        return self._models[self._model_index % len(self._models)]

    def rotate_key(self) -> Optional[str]:
        """轮换到下一个 Key

        Returns:
            新的当前 Key，如果池为空则返回 None
        """
        if not self._keys:
            return None
        self._key_index = (self._key_index + 1) % len(self._keys)
        return self.current_key()

    def mark_failure(self, key: str) -> None:
        """标记 Key 失败"""
        self._failures[key] = self._failures.get(key, 0) + 1

    def degrade(self) -> Optional[str]:
        """降级策略：先换模型，再换 Key

        Returns:
            新的当前 Key，或 None（已耗尽）
        """
        if self._model_index < len(self._models) - 1:
            self._model_index += 1
            return self.current_key()

        if len(self._keys) > 1:
            self._model_index = 0
            return self.rotate_key()

        return None

    def is_exhausted(self) -> bool:
        """检查是否所有降级选项都已耗尽"""
        model_exhausted = self._model_index >= len(self._models) - 1
        key_exhausted = len(self._keys) <= 1
        return model_exhausted and key_exhausted

    def reset(self) -> None:
        """重置所有状态"""
        self._key_index = 0
        self._model_index = 0
        self._failures.clear()

    @property
    def available_keys(self) -> int:
        return len(self._keys)

    @property
    def healthy_keys(self) -> int:
        return sum(1 for k in self._keys
                   if self._failures.get(k, 0) < 3)
