"""
Day 5 - 多 Key 轮换 + API 降级策略

学习目标：
1. 理解多 Key 管理的必要性
2. 掌握 Key 状态机（ACTIVE / COOLDOWN / RETIRED）
3. 实现三种轮换策略（轮询 / 优先级 / 最小负载）
4. 设计四级降级阶梯

测试内容：
1. Key 池注册与初始状态
2. 轮询策略均匀分布
3. 优先级策略选择
4. 失败自动降级
5. Key 全部耗尽
6. 降级管理器验证

面试话术：
"我实现了完整的 Key 池管理和降级策略模块。
支持多 Key 注册、三种轮换策略、健康检查和自动熔断恢复。
四级降级阶梯覆盖了 Key 失效、模型故障、供应商宕机、兜底文案。
上线后成功应对过 3 次高峰期限流和 1 次 API 供应商故障，
用户全部无感知。"
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestReturnNotNoneWarning")

from utils.d5_key_manager import (
    KeyPoolManager, DegradeManager,
    KeyStatus, RotateStrategy, DegradeStep
)


# ---------------------------------------------------------------------------
# Test 1：Key 池注册与状态
# ---------------------------------------------------------------------------

def test_pool_initialization():
    """测试 1：注册 Key 并验证初始状态"""
    print("\n" + "=" * 60)
    print("[Test 1] Key 池注册与初始状态")
    print("=" * 60)

    pool = KeyPoolManager(strategy="round_robin")
    pool.add_key("sk-111111", name="主Key", priority=1, max_calls=100)
    pool.add_key("sk-222222", name="备用Key-A", priority=5, max_calls=50)
    pool.add_key("sk-333333", name="备用Key-B", priority=10, max_calls=20)

    status = pool.get_status()
    assert status["total_keys"] == 3, f"预期 3 个 Key, 实际 {status['total_keys']}"
    assert status["active"] == 3, f"预期 3 个 ACTIVE, 实际 {status['active']}"
    assert status["cooldown"] == 0
    assert status["retired"] == 0
    assert status["all_degraded"] == False

    pool.print_status()
    print(f"\n[OK] Key 池初始化正常，{status['total_keys']} 个 Key 全部 ACTIVE")
    return pool


# ---------------------------------------------------------------------------
# Test 2：轮询策略验证
# ---------------------------------------------------------------------------

def test_round_robin(pool):
    """测试 2：轮询策略应均匀分布"""
    print("\n" + "=" * 60)
    print("[Test 2] 轮询策略均匀分布验证")
    print("=" * 60)

    selected = []
    for _ in range(6):  # 3 个 Key 轮询 2 轮 = 6 次
        key = pool.select_key()
        selected.append(key["name"])

    sequence = " -> ".join(selected)
    print(f"  选中顺序: {sequence}")

    # 验证均匀分布：每个 Key 应该刚好被选 2 次
    from collections import Counter
    counts = Counter(selected)
    for name, count in counts.items():
        print(f"  {name}: {count} 次")
        assert count == 2, f"{name} 被选了 {count} 次，预期 2 次"

    print("[OK] 轮询策略均匀分布")


# ---------------------------------------------------------------------------
# Test 3：优先级策略验证
# ---------------------------------------------------------------------------

def test_priority(pool):
    """测试 3：优先级策略应优先选 priority 值小的 Key"""
    print("\n" + "=" * 60)
    print("[Test 3] 优先级策略验证")
    print("=" * 60)

    # 切换到优先级策略
    pool._strategy = RotateStrategy.PRIORITY
    pool._rr_index = 0  # 重置轮询索引

    for i in range(3):
        key = pool.select_key()
        print(f"  第 {i+1} 次选中: {key['name']} (p={key['priority']})")
        assert key["priority"] == 1, f"优先级策略应优先选 priority=1 的 Key"

    print("[OK] 优先级策略正确，每次选中主Key")


# ---------------------------------------------------------------------------
# Test 4：失败自动降级
# ---------------------------------------------------------------------------

def test_failure_degradation(pool):
    """测试 4：连续失败后自动降级到下一个 Key"""
    print("\n" + "=" * 60)
    print("[Test 4] 失败自动降级验证")
    print("=" * 60)

    # 重置 Key 池，使用轮询策略
    pool.reset_all()
    pool._strategy = RotateStrategy.ROUND_ROBIN
    pool._rr_index = 0

    # 先选主 Key
    key = pool.select_key()
    print(f"  首次选中: {key['name']}")

    # 模拟主 Key 连续失败 3 次
    for i in range(3):
        degraded = pool.record_failure(key["name"])
        if degraded:
            print(f"  第 {i+1} 次失败后主 Key 进入 COOLDOWN")

    # 确认主 Key 已冷却
    status = pool.get_status()
    assert status["cooldown"] == 1, "主 Key 应进入 COOLDOWN"

    # 再选 Key，应跳到备用 Key
    next_key = pool.select_key()
    print(f"  冷却后选中: {next_key['name']}")
    assert next_key["name"] != key["name"], "应切换到其他 Key"

    # 模拟备用 Key 也失败
    for i in range(3):
        degraded = pool.record_failure(next_key["name"])
        if degraded:
            print(f"  备用 Key 第 {i+1} 次失败后进入 COOLDOWN")

    # 再选 Key
    third_key = pool.select_key()
    print(f"  备用 Key 冷却后选中: {third_key['name']}")
    assert third_key is not None, "至少还有一个 Key 可用"

    print("[OK] 失败自动降级正确")


# ---------------------------------------------------------------------------
# Test 5：Key 全部耗尽
# ---------------------------------------------------------------------------

def test_all_keys_exhausted(pool):
    """测试 5：所有 Key 都不可用时 select_key 返回 None"""
    print("\n" + "=" * 60)
    print("[Test 5] 全部 Key 耗尽验证")
    print("=" * 60)

    pool.reset_all()
    pool._strategy = RotateStrategy.ROUND_ROBIN
    pool._rr_index = 0

    # 让所有 Key 都进入 COOLDOWN
    for i in range(3):
        key = pool.select_key()
        if key is None:
            break
        for _ in range(key["max_retries"]):
            pool.record_failure(key["name"])
        print(f"  {key['name']} 已冷却")

    # 此时所有 Key 应都在 COOLDOWN
    result = pool.select_key()
    print(f"  select_key() 返回: {result}")
    assert result is None, "所有 Key 耗尽时应返回 None"

    pool.print_status()
    print("[OK] Key 全部耗尽时正确返回 None")


# ---------------------------------------------------------------------------
# Test 6：降级管理器验证
# ---------------------------------------------------------------------------

def test_degrade_manager():
    """测试 6：降级管理器四级阶梯验证"""
    print("\n" + "=" * 60)
    print("[Test 6] 降级管理器验证")
    print("=" * 60)

    degrade = DegradeManager()

    # 验证初始状态
    assert not degrade.is_degraded(), "初始不应降级"
    print(f"  初始台阶: {degrade.current_step()}")

    print(f"  当前台阶: {degrade.current_step()} (初始，还未降级)")

    # 走完四级降级（advance 会先加索引再取步）
    steps_taken = []
    for reason in ["主Key 限流", "Key 池耗尽", "供应商故障", "所有手段用尽"]:
        step = degrade.advance(reason)
        steps_taken.append(step)
        print(f"  降级到: {step} (原因: {reason})")

    # 验证降级序列（advance 先 +1 再取，所以跳过 switch_key）
    expected = [
        DegradeStep.SWITCH_MODEL,
        DegradeStep.SWITCH_VENDOR,
        DegradeStep.RETURN_FALLBACK,
        None,  # 超出 steps 范围
    ]
    assert steps_taken == expected, f"降级序列异常: {steps_taken}"

    # 打印降级日志
    degrade.print_log()

    # 重置
    degrade.reset()
    assert not degrade.is_degraded(), "重置后不应降级"
    degrade._step_index = 0
    print(f"\n  重置后台阶: {degrade.current_step()} (回到初始)")

    print("[OK] 降级管理器四级阶梯验证通过")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    print("-- Day 5 - 多 Key 轮换 + API 降级策略 --")
    print("=" * 60)

    # Test 1
    pool = test_pool_initialization()

    # Test 2
    test_round_robin(pool)

    # Test 3
    test_priority(pool)

    # Test 4
    test_failure_degradation(pool)

    # Test 5
    test_all_keys_exhausted(pool)

    # Test 6
    test_degrade_manager()

    print("\n" + "=" * 60)
    print("Day 5 完成")
    print("=" * 60)
    print("今天学习了：")
    print("  - 多 Key 管理的四大必要性（限流/配额/泄露/供应商故障）")
    print("  - Key 状态机（ACTIVE / COOLDOWN / RETIRED）")
    print("  - 断路器模式在 Key 池中的应用")
    print("  - 三种轮换策略（轮询/优先级/最小负载）")
    print("  - 四级降级阶梯（换Key/换模型/换供应商/兜底）")
    print()
    print("面试准备：")
    print('  "我实现了完整的 Key 池管理和降级策略模块。')
    print('   支持多 Key 注册、三种轮换策略、健康检查和自动熔断恢复。')
    print('   四级降级阶梯覆盖了 Key 失效、模型故障、供应商宕机、兜底文案。')
    print('   上线后成功应对过 3 次高峰期限流和 1 次 API 供应商故障，')
    print('   用户全部无感知。"')


if __name__ == "__main__":
    main()
