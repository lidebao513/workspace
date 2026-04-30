# Day 33 — 集成测试 + 全模块报告

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

## 八、产出物

- `tests/test_integration.py` — 55 个集成测试

## 九、自检清单

- [ ] 分组测试能独立运行
- [ ] 集成报告包含 module/total/passed/failed/duration
- [ ] 失败时记录到 details
- [ ] 全量测试通过后无多余 artifact
- [ ] 独立模块函数验证正常
