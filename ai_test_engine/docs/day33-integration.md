# Day 33 — 集成测试 + 全模块报告

## 学习目标

1. 理解单元测试与集成测试的区别，学会设计集成测试用例
2. 掌握按模块分组报告的方法，学会生成结构化的测试报告
3. 理解 TestLoader 的使用，学会动态加载测试类
4. 掌握全模块集成的方法，学会验证模块间的协作

## 一、引言

单体测试通过不代表项目能跑通。集成测试把所有模块串联起来跑，并生成全模块报告。

## 二、前置知识讲解

### 2.1 单元测试 vs 集成测试

**一句话定义：** 单元测试测"零件"——一个类一个方法；集成测试测"流水线"——零件组装后能不能正常运转。

**类比：**
- 单元测试：检查车灯亮不亮、刹车片厚度够不够
- 集成测试：踩刹车时灯会亮吗？（刹车→灯光联动）

**面试话术：** "我见过把集成测试写成单元测试 2.0 的——每个分组独立测但互不感知。真正的集成测试应该验证 A 模块的输出是 B 模块可接受的输入。"

### 2.2 按模块分组报告

**一句话定义：** 不是把 100 个测试扔一起，而是按质量/安全/性能等模块分组，每个组独立报告通过/失败/耗时。

**设计：**
```python
IntegrationReport(
    module="Quality",
    total=13,              # 该模块总用例
    passed=13,
    failed=0,
    duration=0.02,         # 该模块耗时
    details=["[!!] ..."]   # 仅失败时记录
)
```

**面试话术：** "全量 161 测试跑完只知道 'PASS/FAIL'。分组报告告诉你 'security 14/14 PASS, quality 1/13 FAIL'——问题定位从 5 分钟缩到 30 秒。"

## 三、需求分析

55 个测试用例：
- 3 个分组测试（quality/security/performance）
- 1 个全局汇总
- 1 个独立模块函数可用性验证

## 四、代码说明

### test_integration.py
- `_run_group()` — 通用分组执行器，用 TestLoader 加载测试类
- `test_quality_module` — 加载 QualityScore/LLMJudge/AssessmentPipeline
- `test_security_module` — 加载 InjectionTester/RobustnessTester/RegressionTester
- `test_performance_module` — 加载 LoadTester/CircuitBreaker/TokenAuditor
- `test_integration_summary` — 加载 smoke 模块生成总报告
- `test_standalone_module_functions` — 无测试框架直接调用模块函数

### 分组报告格式
```json
{
  "module": "Quality",
  "total": 13,
  "passed": 13,
  "failed": 0,
  "duration": 0.02,
  "details": []
}
```

## 五、运行结果

```
55 passed (integration: 55)
```

## 六、工作场景

- 上线前全量回归
- CI 流程中作为整体质量门禁
- 模块交接——新模块上线先看集成测试报告

## 七、面试问题

**Q: test_integration 为什么要 include 模块的测试类而不是直接 import?**
A: 因为模块的测试类不是导出的公共接口。通过 TestLoader 加载而不是 import 之后继承，能确保每个模块的测试是**独立的**——改集成测试不会意外影响模块测试。

**Q: 分组报告的 details 为什么只记录失败？**
A: 通过的测试不需要留痕迹——成功了就是成功了。只记录失败 + 前 80 字符堆栈，让报告可读性优先。

**Q: 集成测试和单元测试的核心区别是什么？**
A: 单元测试测单个"零件"（类/方法），使用 Mock 隔离依赖；集成测试测"流水线"（多个模块协作），验证模块间的数据流转和接口兼容性。

**Q: 如何设计有效的集成测试用例？**
A: 集成测试应该验证模块之间的协作：比如 Settings 的输出是否能被 AIEngineClient 正确消费，KeyManager 的降级策略是否能被 ErrorHandler 正确触发。重点关注数据流转和异常边界。

## 八、代码示例

### 集成测试框架实现

```python
import unittest
import time
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class IntegrationReport:
    """集成测试报告"""
    module: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    duration: float = 0.0
    details: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """计算通过率"""
        if self.total == 0:
            return 0.0
        return self.passed / self.total

class IntegrationTester:
    """集成测试执行器"""
    
    def _run_group(self, module_name: str, test_classes: List) -> IntegrationReport:
        """运行指定模块的测试组"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        for test_class in test_classes:
            suite.addTests(loader.loadTestsFromTestCase(test_class))
        
        start_time = time.time()
        runner = unittest.TextTestRunner(verbosity=0)
        result = runner.run(suite)
        duration = time.time() - start_time
        
        # 收集失败详情
        details = []
        for failure in result.failures:
            test_name = str(failure[0])
            error_msg = str(failure[1])[:80]  # 只保留前 80 字符
            details.append(f"[FAIL] {test_name}: {error_msg}")
        
        for error in result.errors:
            test_name = str(error[0])
            error_msg = str(error[1])[:80]
            details.append(f"[ERROR] {test_name}: {error_msg}")
        
        return IntegrationReport(
            module=module_name,
            total=result.testsRun,
            passed=result.testsRun - len(result.failures) - len(result.errors),
            failed=len(result.failures) + len(result.errors),
            duration=round(duration, 2),
            details=details
        )
    
    def run_all(self, modules: Dict[str, List]) -> Dict[str, IntegrationReport]:
        """运行所有模块的集成测试"""
        reports = {}
        for module_name, test_classes in modules.items():
            reports[module_name] = self._run_group(module_name, test_classes)
        return reports
    
    def generate_summary(self, reports: Dict[str, IntegrationReport]) -> dict:
        """生成全局汇总报告"""
        total_tests = sum(r.total for r in reports.values())
        total_passed = sum(r.passed for r in reports.values())
        total_failed = sum(r.failed for r in reports.values())
        total_duration = sum(r.duration for r in reports.values())
        
        return {
            'modules': {k: v.__dict__ for k, v in reports.items()},
            'summary': {
                'total': total_tests,
                'passed': total_passed,
                'failed': total_failed,
                'success_rate': round(total_passed / total_tests * 100, 2) if total_tests > 0 else 0,
                'duration': round(total_duration, 2)
            }
        }

# 示例测试类（模拟）
class TestQualityModule(unittest.TestCase):
    def test_quality_score(self):
        pass
    
    def test_llm_judge(self):
        pass

class TestSecurityModule(unittest.TestCase):
    def test_injection_detection(self):
        pass
    
    def test_robustness(self):
        pass

class TestPerformanceModule(unittest.TestCase):
    def test_circuit_breaker(self):
        pass
    
    def test_token_auditor(self):
        pass

# 使用示例
if __name__ == "__main__":
    tester = IntegrationTester()
    
    # 定义模块测试类映射
    test_modules = {
        'Quality': [TestQualityModule],
        'Security': [TestSecurityModule],
        'Performance': [TestPerformanceModule]
    }
    
    # 运行集成测试
    reports = tester.run_all(test_modules)
    
    # 生成汇总报告
    summary = tester.generate_summary(reports)
    
    print("=== 集成测试报告 ===")
    for module, report in reports.items():
        print(f"\n{module}:")
        print(f"  总计: {report.total}, 通过: {report.passed}, 失败: {report.failed}")
        print(f"  耗时: {report.duration}s, 通过率: {report.success_rate*100:.2f}%")
    
    print("\n=== 全局汇总 ===")
    print(f"总测试数: {summary['summary']['total']}")
    print(f"通过: {summary['summary']['passed']}, 失败: {summary['summary']['failed']}")
    print(f"总耗时: {summary['summary']['duration']}s")
    print(f"总通过率: {summary['summary']['success_rate']}%")
```

## 九、产出物

- `tests/test_integration.py` — 55 个集成测试

## 十、练习题

1. **基础题：** 扩展 `IntegrationReport` 类，添加 `success_rate` 属性的计算方法。

2. **进阶题：** 为 `IntegrationTester` 添加 `export_report()` 方法，支持将报告导出为 JSON 和 HTML 格式。

3. **挑战题：** 实现一个 `DependencyGraph` 类，能够分析模块之间的依赖关系，并按正确的顺序运行集成测试。

## 十一、自检清单

- [ ] 分组测试能独立运行
- [ ] 集成报告包含 module/total/passed/failed/duration
- [ ] 失败时记录到 details
- [ ] 全量测试通过后无多余 artifact
- [ ] 独立模块函数验证正常
