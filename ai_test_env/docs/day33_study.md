# Day 33 — Token 审计 + 多语言 + 压测集成

## 学习目标

1. 理解 Token 审计与异常检测的实际应用
2. 掌握多语言检测器对不同语言的识别能力
3. 理解压测方案的三种模式
4. 学会把多个模块的输出整合为一个统一报告

---

## 一、今日目标

> 三件事合一把手：用 d26 TokenAuditor 审计真实 API 费用、用 d8e 多语言检测验证中英日回复、规划 d22 压测方案。Phase 1（API 实战）的最后一天。

- 理解 Token 审计与异常检测的实际应用
- 掌握多语言检测器对不同语言的识别能力
- 理解压测方案的三种模式
- 学会把多个模块的输出整合为一个统一报告

---

## 二、三件事的管道

```
D31 API 日志 (run_logs/d31_api_*.json)
  │
  ├── TokenAuditor.record_call()
  │     └── prompt_tokens + completion_tokens → 费用 + 异常检测
  │
  ├── LanguageDetector.detect()
  │     └── 回复文本 → "zh" / "en" / "ja" / "code"
  │
  └── LoadTestPlan（方案描述）
        └── 3 种压测模式说明
  │
  └── d33_integration_*.json（综合报告）
```

---

## 三、Token 审计输出

```
总调用: 8
总 Token: 530
总费用: ¥0.00091（≈ 0.09 分）
异常检测: 无异常
```

---

## 四、多语言检测

| Label | 回复 | 检测 | 预期 | 结果 |
|-------|------|------|------|:----:|
| cn_basic | 人工智能... | zh | zh | ✅ |
| en_basic | Machine learning... | en | en | ✅ |
| jp_basic | 人工知能... | ja | ja | ✅ |
| code_generation | def binary_search... | code | code | ✅ |

---

## 五、压测方案

通过 d22 LoadTester 接口，提供三种方案：

| 名称 | 模式 | 描述 |
|------|------|------|
| steady_3 | 稳态 | 3 并发 × 10 次请求 |
| step_2_to_10 | 阶梯 | 2→5→10 逐级增加 |
| spike_10 | 突发 | 2 基准 → 10 突发 |

> 实际执行需要配置 DEEPSEEK_API_KEY，每次压测约消耗 ¥0.02。

---

## 六、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| Token 审计 | 3 条 OK 记录 | total_calls=3 |
| Token 审计空 | 空 results | total_calls=0 |
| 多语言 | 中文/英文/代码 | 正确检测 |
| 多语言空 | 空 results | total_checked=0 |
| 日志加载 | 无日志 | 返回 {} |
| 压测方案 | 调用 | 3 个 profile |

---

## 面试题

### 题目 1：如何设计多模块集成的统一报告系统？

**参考答案：**

**集成报告的核心价值：**

当多个独立模块需要协同工作时，统一的报告系统可以：
- 提供全局视角的质量状态
- 汇总各模块的关键指标
- 简化问题定位和根因分析

**统一报告架构：**

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ModuleStatus(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ModuleReport:
    """模块报告"""
    module_name: str
    status: ModuleStatus
    metrics: Dict[str, Any]
    summary: str
    details: Optional[str] = None


@dataclass
class IntegrationReport:
    """集成报告"""
    timestamp: str
    total_modules: int
    successful: int
    warnings: int
    failed: int
    module_reports: List[ModuleReport] = field(default_factory=list)
    overall_status: ModuleStatus = ModuleStatus.SUCCESS
    total_cost: float = 0.0
    total_tokens: int = 0


class IntegrationReporter:
    """集成报告器"""

    def __init__(self):
        self._reports: List[ModuleReport] = []

    def add_report(self, report: ModuleReport) -> "IntegrationReporter":
        """添加模块报告"""
        self._reports.append(report)
        return self

    def build(self) -> IntegrationReport:
        """构建集成报告"""
        successful = sum(1 for r in self._reports if r.status == ModuleStatus.SUCCESS)
        warnings = sum(1 for r in self._reports if r.status == ModuleStatus.WARNING)
        failed = sum(1 for r in self._reports if r.status == ModuleStatus.ERROR)

        if failed > 0:
            overall_status = ModuleStatus.ERROR
        elif warnings > 0:
            overall_status = ModuleStatus.WARNING
        else:
            overall_status = ModuleStatus.SUCCESS

        total_cost = sum(
            r.metrics.get("cost", 0.0)
            for r in self._reports
        )
        total_tokens = sum(
            r.metrics.get("total_tokens", 0)
            for r in self._reports
        )

        return IntegrationReport(
            timestamp=datetime.now().isoformat(),
            total_modules=len(self._reports),
            successful=successful,
            warnings=warnings,
            failed=failed,
            module_reports=self._reports,
            overall_status=overall_status,
            total_cost=total_cost,
            total_tokens=total_tokens
        )

    def render(self) -> str:
        """渲染报告"""
        report = self.build()

        lines = [
            "━━━ 综合集成报告 ━━━",
            f"时间: {report.timestamp}",
            f"模块数: {report.total_modules}",
            f"成功: {report.successful} | 警告: {report.warnings} | 失败: {report.failed}",
            "",
            "── 各模块详情 ──"
        ]

        for mr in report.module_reports:
            icon = "✓" if mr.status == ModuleStatus.SUCCESS else (
                "⚠" if mr.status == ModuleStatus.WARNING else "✗"
            )
            lines.append(f"  {icon} {mr.module_name}: {mr.summary}")

        if report.total_cost > 0:
            lines.extend(["", f"总费用: ¥{report.total_cost:.4f}"])
        if report.total_tokens > 0:
            lines.append(f"总Token: {report.total_tokens}")

        return "\n".join(lines)
```

---

### 题目 2：如何设计一个支持多语言的检测系统？

**参考答案：**

**多语言检测的核心算法：**

基于字符集和词汇特征的语言检测：
- 中日韩文字符（CJK）识别
- 拉丁字符集分析
- 特殊词汇匹配
- N-gram 语言模型

**实现方案：**

```python
import re
from typing import Dict, Optional
from collections import Counter


class LanguageType(Enum):
    ZH = "zh"
    EN = "en"
    JA = "ja"
    CODE = "code"
    UNKNOWN = "unknown"


class LanguageDetector:
    """多语言检测器"""

    CJK_RANGE = r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]'
    JAPANESE_HIRAGANA = r'[\u3040-\u309f]'
    JAPANESE_KATAKANA = r'[\u30a0-\u30ff]'

    CODE_INDICATORS = {
        "python", "def ", "class ", "import ",
        "javascript", "function", "const ", "let ",
        "java", "public ", "private ",
        "if (", "for (", "while ("
    }

    def detect(self, text: str) -> str:
        """检测语言类型"""
        if not text or not text.strip():
            return LanguageType.UNKNOWN.value

        if self._is_code(text):
            return LanguageType.CODE.value

        cjk_count = len(re.findall(self.CJK_RANGE, text))
        total_chars = len(text.strip())

        if cjk_count / total_chars > 0.3:
            if self._is_japanese(text):
                return LanguageType.JA.value
            return LanguageType.ZH.value

        latin_count = len(re.findall(r'[a-zA-Z]', text))
        if latin_count / total_chars > 0.5:
            return LanguageType.EN.value

        return LanguageType.UNKNOWN.value

    def _is_code(self, text: str) -> bool:
        """检测是否为代码"""
        text_lower = text.lower()
        for indicator in self.CODE_INDICATORS:
            if indicator in text_lower:
                return True

        bracket_count = text.count("{") + text.count("}") + \
                       text.count("(") + text.count(")")
        if bracket_count > 5:
            return True

        return False

    def _is_japanese(self, text: str) -> bool:
        """检测是否为日语"""
        hiragana_count = len(re.findall(self.JAPANESE_HIRAGANA, text))
        katakana_count = len(re.findall(self.JAPANESE_KATAKANA, text))

        return hiragana_count > 0 or katakana_count > 0

    def get_confidence(self, text: str) -> float:
        """获取检测置信度"""
        lang = self.detect(text)
        if lang == LanguageType.UNKNOWN.value:
            return 0.0

        cjk_count = len(re.findall(self.CJK_RANGE, text))
        total = len(text.strip())

        if lang in (LanguageType.ZH.value, LanguageType.JA.value):
            return min(1.0, cjk_count / max(1, total))
        elif lang == LanguageType.EN.value:
            latin = len(re.findall(r'[a-zA-Z]', text))
            return min(1.0, latin / max(1, total))
        elif lang == LanguageType.CODE.value:
            return 0.8

        return 0.5
```

---

## 代码示例

```python
"""
Day 33 代码示例：Token审计+多语言+压测集成完整实现
演示多模块集成和统一报告
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
from enum import Enum
import re


class ModuleStatus(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class LanguageType(Enum):
    ZH = "zh"
    EN = "en"
    JA = "ja"
    CODE = "code"
    UNKNOWN = "unknown"


@dataclass
class ModuleReport:
    module_name: str
    status: ModuleStatus
    metrics: Dict[str, Any]
    summary: str


@dataclass
class IntegrationReport:
    timestamp: str
    total_modules: int
    successful: int
    warnings: int
    failed: int
    module_reports: List[ModuleReport] = field(default_factory=list)


class LanguageDetector:
    CJK_RANGE = r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]'
    CODE_KEYWORDS = {"def ", "function", "class ", "import ", "const "}

    def detect(self, text: str) -> str:
        if not text or not text.strip():
            return LanguageType.UNKNOWN.value
        if self._is_code(text):
            return LanguageType.CODE.value
        cjk_count = len(re.findall(self.CJK_RANGE, text))
        if cjk_count / len(text) > 0.3:
            return LanguageType.ZH.value
        latin_count = len(re.findall(r'[a-zA-Z]', text))
        if latin_count / len(text) > 0.5:
            return LanguageType.EN.value
        return LanguageType.UNKNOWN.value

    def _is_code(self, text: str) -> bool:
        return any(kw in text.lower() for kw in self.CODE_KEYWORDS)


class TokenAuditor:
    INPUT_COST_PER_M = 1.0
    OUTPUT_COST_PER_M = 2.0

    def __init__(self):
        self._records: List[Dict] = []

    def record_call(self, prompt_tokens: int, completion_tokens: int) -> None:
        total = prompt_tokens + completion_tokens
        cost = (prompt_tokens * self.INPUT_COST_PER_M + completion_tokens * self.OUTPUT_COST_PER_M) / 1_000_000
        self._records.append({
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
            "cost": cost
        })

    def get_summary(self) -> Dict[str, Any]:
        if not self._records:
            return {"total_calls": 0, "total_cost": 0.0}
        return {
            "total_calls": len(self._records),
            "total_tokens": sum(r["total_tokens"] for r in self._records),
            "total_cost": sum(r["cost"] for r in self._records)
        }


class LoadTestPlan:
    """压测方案"""

    def describe(self) -> str:
        return """
三种压测模式：
1. 渐进式：逐步增加并发，从1到100
2. 脉冲式：瞬间高并发，测试峰值处理能力
3. 稳定式：固定并发，持续压测稳定性和性能
        """


class IntegrationReporter:
    def __init__(self):
        self._reports: List[ModuleReport] = []

    def add_report(self, report: ModuleReport) -> "IntegrationReporter":
        self._reports.append(report)
        return self

    def build(self) -> IntegrationReport:
        successful = sum(1 for r in self._reports if r.status == ModuleStatus.SUCCESS)
        warnings = sum(1 for r in self._reports if r.status == ModuleStatus.WARNING)
        failed = sum(1 for r in self._reports if r.status == ModuleStatus.ERROR)

        return IntegrationReport(
            timestamp=datetime.now().isoformat(),
            total_modules=len(self._reports),
            successful=successful,
            warnings=warnings,
            failed=failed,
            module_reports=self._reports
        )

    def render(self) -> str:
        report = self.build()
        lines = ["━━━ Phase 1 综合报告 ━━━",
                 f"时间: {report.timestamp}",
                 f"模块数: {report.total_modules}",
                 f"成功: {report.successful} | 警告: {report.warnings} | 失败: {report.failed}",
                 ""]
        for mr in report.module_reports:
            icon = "✓" if mr.status == ModuleStatus.SUCCESS else ("⚠" if mr.status == ModuleStatus.WARNING else "✗")
            lines.append(f"  {icon} {mr.module_name}: {mr.summary}")
        return "\n".join(lines)


def demo():
    print("=" * 60)
    print("Day 33 代码示例：多模块集成演示")
    print("=" * 60)

    print("\n[1] 多语言检测")
    print("-" * 40)
    detector = LanguageDetector()
    test_texts = [
        "人工智能是计算机科学的重要分支",
        "Machine learning is important",
        '{"result": "success"}'
    ]
    for text in test_texts:
        lang = detector.detect(text)
        print(f"  '{text[:20]}...' -> {lang}")

    print("\n[2] Token 审计")
    print("-" * 40)
    auditor = TokenAuditor()
    auditor.record_call(100, 50)
    auditor.record_call(200, 100)
    summary = auditor.get_summary()
    print(f"  总调用: {summary['total_calls']}")
    print(f"  总费用: ¥{summary['total_cost']:.6f}")

    print("\n[3] 压测方案")
    print("-" * 40)
    plan = LoadTestPlan()
    print(plan.describe())

    print("\n[4] 集成报告")
    print("-" * 40)
    reporter = IntegrationReporter()
    reporter.add_report(ModuleReport("TokenAuditor", ModuleStatus.SUCCESS, summary, "审计完成"))
    reporter.add_report(ModuleReport("LanguageDetector", ModuleStatus.SUCCESS, {}, "检测完成"))
    print(reporter.render())

    print("\n" + "=" * 60)
    print("Phase 1 完成 ✅")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现异常 Token 检测

**要求：**
扩展 TokenAuditor，添加异常检测功能，识别异常的 Token 消耗。

**提示：**
```python
class AnomalyDetector:
    """异常检测器"""
    def __init__(self):
        self._baseline: List[int] = []

    def add_baseline(self, tokens: int) -> None:
        """添加基线数据"""
        pass

    def is_anomaly(self, tokens: int) -> bool:
        """判断是否异常"""
        pass
```

**验收标准：**
- 基于历史数据计算平均值和标准差
- 超出 2 个标准差判定为异常
- 返回异常类型（过高/过低）

---

### 练习 2：实现多语言统计报告

**要求：**
统计各类语言的回复分布，生成语言分布报告。

**提示：**
```python
class LanguageStatistics:
    """语言统计"""
    def __init__(self):
        self._counts: Dict[str, int] = {}

    def record(self, language: str) -> None:
        """记录语言类型"""
        pass

    def get_distribution(self) -> Dict[str, float]:
        """获取语言分布"""
        pass
```

**验收标准：**
- 统计各语言出现次数
- 计算百分比分布
- 生成排序后的报告

---

### 练习 3：实现压测结果对比

**要求：**
比较不同压测模式的性能结果，生成对比报告。

**提示：**
```python
class LoadTestComparator:
    """压测对比器"""
    def compare(self, results: Dict[str, Dict]) -> str:
        """对比压测结果"""
        pass
```

**验收标准：**
- 对比 RPS、延迟、错误率
- 生成 ASCII 表格
- 标注最佳性能指标

---

## 七、Phase 1 总结

| Day | 模块 | 测试 | 状态 |
|:----|:-----|:----|:----:|
| 31 | API 真调用 | 12/12 | ✅ |
| 32 | 质量评估实战 | 9/9 | ✅ |
| 33 | 审计+多语言+压测 | 7/7 | ✅ |

---

## 八、产出物

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d33_integration.py` | Token 审计+多语言+压测集成 | [OK] |
| `tests/d33_test_integration.py` | 7 个测试 | [OK] 7/7 PASS |
| `day33_study.md` | 本文档 | [OK] |
