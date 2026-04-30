"""
API Key 管理与降级策略模块

功能：多 API Key 集中管理、健康追踪、自动轮换和降级策略。
三种调度策略 + 四级降级阶梯。

面试话术：
    "Key 池和降级策略是我在生产环境碰到真实问题后设计的。
    有次 DeepSeek 海外节点超时，我们自动切换到通义千问，
    2B 客服对话完全没中断。"
"""
import time
import threading
from typing import Optional, List, Dict
from enum import Enum


class KeyStatus(str, Enum):
    ACTIVE = "active"         # 正常可用
    DEGRADED = "degraded"     # 降级（备用 Key，降低权重）
    COOLDOWN = "cooldown"     # 冷却中（限流或连续失败后等待恢复）
    RETIRED = "retired"       # 废弃（永久不可用）


class RotateStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"   # 轮询
    PRIORITY = "priority"         # 优先级
    LEAST_LOAD = "least_load"     # 最小负载


class DegradeStep(str, Enum):
    SWITCH_KEY = "switch_key"            # 台阶1: 换 Key
    SWITCH_MODEL = "switch_model"        # 台阶2: 换模型
    SWITCH_VENDOR = "switch_vendor"      # 台阶3: 换供应商
    RETURN_FALLBACK = "return_fallback"  # 台阶4: 返回兜底


class KeyPoolManager:
    """
    多 API Key 池管理器

    支持注册、健康追踪、断路器、自动恢复、三种调度策略。

    参数：
        strategy: 轮换策略（round_robin / priority / least_load）
        cooldown_seconds: 冷却时间（秒），默认 60
        max_retries: 最大连续失败次数，默认 3

    用法：
        pool = KeyPoolManager(strategy="round_robin")
        pool.add_key("sk-xxx", name="主Key", priority=1)
        pool.add_key("sk-yyy", name="备用Key", priority=5)

        key = pool.select_key()              # 选一个可用 Key
        pool.record_success(key["name"])      # 成功后记录
        pool.record_failure(key["name"])      # 失败后记录（自动降级）
        pool.print_status()                   # 打印状态报告
    """

    def __init__(self, strategy="round_robin", cooldown_seconds=60, max_retries=3):
        self._strategy = RotateStrategy(strategy)
        self._cooldown_seconds = cooldown_seconds
        self._max_retries = max_retries
        self._keys: List[Dict] = []
        self._lock = threading.Lock()
        self._rr_index = 0

    # ---- Key 注册 ----

    def add_key(self, api_key, name="", priority=10, max_retries=None,
                cooldown_seconds=None, max_calls=None):
        """注册一个 API Key"""
        if not name:
            name = f"key_{len(self._keys) + 1}"
        entry = {
            "api_key": api_key,
            "name": name,
            "priority": priority,
            "max_retries": max_retries or self._max_retries,
            "cooldown_seconds": cooldown_seconds or self._cooldown_seconds,
            "max_calls": max_calls or 999999,
            "status": KeyStatus.ACTIVE,
            "fail_count": 0,
            "success_count": 0,
            "total_calls": 0,
            "last_fail_time": None,
            "cooldown_until": None,
        }
        self._keys.append(entry)
        return entry

    def add_keys_from_env(self, prefix="DEEPSEEK_API_KEY"):
        """从环境变量批量注册 Key"""
        import os
        count = 0
        for env_name, env_value in sorted(os.environ.items()):
            if env_name == prefix:
                self.add_key(env_value, name="主Key", priority=1)
                count += 1
            elif env_name.startswith(prefix + "_"):
                suffix = env_name[len(prefix) + 1:]
                self.add_key(env_value, name=f"备用Key-{suffix}", priority=5)
                count += 1
        return count

    # ---- Key 选择 ----

    def select_key(self):
        """按策略选一个可用 Key，全不可用时返回 None"""
        available = self._get_available()
        if not available:
            return None
        if self._strategy == RotateStrategy.ROUND_ROBIN:
            return self._pick_rr(available)
        elif self._strategy == RotateStrategy.PRIORITY:
            return min(available, key=lambda k: (k["priority"], k["total_calls"]))
        elif self._strategy == RotateStrategy.LEAST_LOAD:
            return min(available, key=lambda k: k["total_calls"])
        return available[0]

    def _get_available(self):
        """获取当前可用的 Key 列表（同时处理冷却自动恢复）"""
        now = time.time()
        available = []
        for key in self._keys:
            if key["status"] == KeyStatus.RETIRED:
                continue
            if key["status"] == KeyStatus.COOLDOWN:
                if key.get("cooldown_until") and now >= key["cooldown_until"]:
                    key["status"] = KeyStatus.ACTIVE
                    key["fail_count"] = 0
                    key["cooldown_until"] = None
                    available.append(key)
                continue
            if key["total_calls"] >= key["max_calls"]:
                key["status"] = KeyStatus.RETIRED
                continue
            available.append(key)
        return available

    def _pick_rr(self, available):
        with self._lock:
            idx = self._rr_index % len(available)
            self._rr_index += 1
            return available[idx]

    # ---- 状态记录 ----

    def record_success(self, name):
        """记录一次成功调用，重置连续失败计数"""
        for key in self._keys:
            if key["name"] == name:
                key["success_count"] += 1
                key["total_calls"] += 1
                key["fail_count"] = 0
                if key["status"] == KeyStatus.COOLDOWN:
                    key["status"] = KeyStatus.ACTIVE
                    key["cooldown_until"] = None
                break

    def record_failure(self, name):
        """
        记录一次失败调用
        连续失败达到阈值后自动标记为 COOLDOWN
        返回: True 表示该 Key 已被降级
        """
        for key in self._keys:
            if key["name"] == name:
                key["fail_count"] += 1
                key["total_calls"] += 1
                key["last_fail_time"] = time.time()
                if key["fail_count"] >= key["max_retries"]:
                    key["status"] = KeyStatus.COOLDOWN
                    key["cooldown_until"] = time.time() + key["cooldown_seconds"]
                    return True
                break
        return False

    # ---- 状态查询 ----

    def get_status(self):
        """获取 Key 池整体状态"""
        active = sum(1 for k in self._keys if k["status"] == KeyStatus.ACTIVE)
        cooldown = sum(1 for k in self._keys if k["status"] == KeyStatus.COOLDOWN)
        retired = sum(1 for k in self._keys if k["status"] == KeyStatus.RETIRED)
        return {
            "total_keys": len(self._keys),
            "active": active,
            "cooldown": cooldown,
            "retired": retired,
            "all_degraded": active == 0,
            "keys": [{
                "name": k["name"],
                "status": k["status"].value,
                "priority": k["priority"],
                "fail_count": k["fail_count"],
                "success_count": k["success_count"],
                "total_calls": k["total_calls"],
                "cooldown_until": k.get("cooldown_until"),
            } for k in self._keys],
        }

    def print_status(self):
        status = self.get_status()
        print(f"\n{'=' * 60}")
        print("Key 池状态报告")
        print(f"{'=' * 60}")
        print(f"总 Key 数: {status['total_keys']} | 可用: {status['active']} | "
              f"冷却: {status['cooldown']} | 废弃: {status['retired']}")
        for k in status["keys"]:
            icon = {"active": "[OK]", "degraded": "[--]", "cooldown": "[**]",
                    "retired": "[XX]"}.get(k["status"], "[??]")
            print(f"  {icon} {k['name']:>10s} (p={k['priority']}) "
                  f"成功={k['success_count']} 失败={k['fail_count']} 总计={k['total_calls']}")

    def get_active_count(self):
        return len(self._get_available())

    def reset_all(self):
        for key in self._keys:
            key["status"] = KeyStatus.ACTIVE
            key["fail_count"] = 0
            key["success_count"] = 0
            key["total_calls"] = 0
            key["last_fail_time"] = None
            key["cooldown_until"] = None


class DegradeManager:
    """
    API 降级管理器

    四级降级阶梯：
        1. switch_key      -> 换 Key
        2. switch_model    -> 换更便宜的模型
        3. switch_vendor   -> 换供应商
        4. return_fallback -> 返回兜底内容

    用法：
        degrade = DegradeManager()
        degrade.advance(reason="所有 Key 限流")
        step = degrade.current_step()
    """

    def __init__(self, steps=None):
        self.steps = steps or [
            DegradeStep.SWITCH_KEY,
            DegradeStep.SWITCH_MODEL,
            DegradeStep.SWITCH_VENDOR,
            DegradeStep.RETURN_FALLBACK,
        ]
        self._step_index = 0
        self._log = []

    def reset(self):
        self._step_index = 0

    def is_degraded(self):
        return self._step_index > 0

    def current_step(self):
        if self._step_index < len(self.steps):
            return self.steps[self._step_index]
        return None

    def advance(self, reason=""):
        self._step_index += 1
        step_name = self.current_step()
        self._log.append({
            "timestamp": time.time(),
            "from": self.steps[self._step_index - 1] if self._step_index > 0 else "normal",
            "to": step_name,
            "reason": reason,
        })
        return step_name

    def print_log(self):
        if not self._log:
            print("无降级记录")
            return
        print(f"\n{'=' * 60}")
        print("降级历史")
        for entry in self._log:
            print(f"  [{entry['timestamp']:.0f}] {entry.get('from','?')} -> {entry['to']}")
            if entry["reason"]:
                print(f"    原因: {entry['reason']}")

    def print_steps(self):
        info = {
            DegradeStep.SWITCH_KEY:      ("切换 Key", "换 Key 池下一个可用 Key", False),
            DegradeStep.SWITCH_MODEL:    ("切换模型", "使用备用模型", False),
            DegradeStep.SWITCH_VENDOR:   ("切换供应商", "使用备用供应商 API", False),
            DegradeStep.RETURN_FALLBACK: ("返回兜底", "返回预设文案", True),
        }
        print(f"\n{'=' * 60}")
        print("降级阶梯")
        for i, s in enumerate(self.steps):
            name, desc, visible = info.get(s, (s, "", False))
            print(f"  台阶{i+1}: {name} - {desc}")
            print(f"         用户感知: {'是' if visible else '否'}")
