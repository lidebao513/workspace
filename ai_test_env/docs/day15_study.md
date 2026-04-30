# Day 15 — E2E 业务场景测试

## 一、今日目标

> 学会构建完整的端到端（E2E）业务场景测试，将多轮对话、安全检测、规则判定整合为场景级测试流水线。

- 理解 E2E 测试在 AI 测试中的定位
- 掌握业务场景模板的设计（5 个内置场景）
- 学会场景执行引擎（多轮对话 + 判定 + 召回率）
- 能生成场景级评分报告

---

## 二、前置知识讲解

### 2.1 什么是 E2E 测试？

**一句话定义：** E2E（End-to-End）测试是从用户视角出发，模拟一个完整的业务流程，验证系统在处理全流程中的表现。

**对比金字塔：**

```
     /\
    /  \        E2E 测试 — 模拟完整业务流程，慢但真实
   /    \
  / Unit \      单元测试 — 测试单个函数，快但覆盖面窄
 /________\
```

**AI 测试 vs 传统 E2E 的差异：**

| 维度 | 传统 E2E | AI E2E |
|------|---------|--------|
| 输入 | 固定的 | 自然语言（多轮） |
| 期望 | 精确输出 | 语义/规则判定 |
| 评估 | 通过/失败 | 通过率 + 安全 + 质量 |
| 工具 | Selenium/Cypress | 场景引擎 + 规则器 |

**面试话术：**
> "E2E 测试是我项目中最高级别的测试。它不像单元测试那样只测一个 API 调用，而是从用户视角模拟一个完整的业务流程——比如客户打电话进来要求更换绑定银行卡。整个过程涉及 8 轮对话，需要验证模型是否能识别用户意图、记住关键信息、拒绝越狱尝试、保持回复礼貌。我把 Day 6-14 的工具都整合进 E2E 流水线，每个场景输出一个多维评分。"

---

### 2.2 业务场景三要素

| 要素 | 说明 | 示例 |
|------|------|------|
| 场景模板 | 预定义的对话流程 | "客服-修改个人信息" |
| 轮次序列 | 每轮的预期关键词和限制 | 第 1 轮期望含"修改"+"手机号" |
| 判定规则 | 每轮回复的检查标准 | 关键词包含、关键词排除、长度范围 |

---

### 2.3 内置场景库

| ID | 场景名称 | 类型 | 轮数 | 重点验证 |
|----|---------|------|------|---------|
| SC-CS-001 | 客服-个人信息修改 | 客服 | 3 | 信息保持 + 关键词 |
| SC-CS-002 | 客服-订单状态查询 | 客服 | 3 | 订单号上下文保持 |
| SC-FIN-001 | 金融-余额查询 | 金融 | 2 | 金额 + 安全拒绝 |
| SC-SEC-001 | 安全-恶意请求拒绝 | 安全 | 2 | 必须拒绝注入 |
| SC-CR-001 | 创意-文案草稿生成 | 创意 | 2 | 内容质量 + 长度控制 |

---

## 三、需求分析

### 3.1 为什么需要 E2E 场景测试

| 维度 | 单点测试 | 场景测试 |
|------|---------|---------|
| 覆盖范围 | 单一 API/功能 | 完整业务流程 |
| 发现的问题 | 接口错误、格式错误 | 意图误解、信息丢失、安全绕过 |
| 排障成本 | 低 | 高（但更贴近生产） |
| 自动化收益 | 中等 | 高（一次编写多次使用） |

### 3.2 测试策略
- **冒烟测试**：每次部署前跑所有场景的简化版
- **回归测试**：每次 Prompt 变更跑所有场景的完整版
- **定期巡检**：每周跑一次全量场景，观察通过率趋势

---

## 四、代码设计

### 4.1 模块结构

```
ScenarioLibrary                   ← 场景模板库
├── 5 个内置业务场景（客服x2 + 金融 + 安全 + 创意）
├── get() / all() / filter_by_type()
└── add_turn() 构建多轮对话

ScenarioEngine                    ← 场景执行引擎
├── run_scenario()                执行单个场景
├── _judge()                      规则判定（关键词+长度）
├── _extract_info()               提取用户信息
└── _calc_context_recall()        计算上下文召回率

E2ETester                         ← E2E 运行器
├── run_all()                     执行全部场景
└── run()                         执行选定的场景
```

### 4.2 场景模板示例

```python
Scenario(id="SC-CS-002", name="客服-订单状态查询",
          type=CUSTOMER_SERVICE)
  turn 0: "帮我查一下我的订单"
           → expected: ["订单", "查"]
           → forbidden: ["拒绝"]
  turn 1: "订单号是 ORD-2024-8888"
           → expected: ["8888", "订单"]
           → min_length: 10
  turn 2: "我刚才说的订单号是多少？"
           → expected: ["8888", "ORD"]
           → 验证上下文保持
```

### 4.3 执行流程

```
对每个场景：
  1. 依次处理每轮用户输入
  2. 获取模型回复（离线 mock 或 API）
  3. 对回复做规则判定：
     - expected_keywords → 必须全都出现
     - forbidden_keywords → 不能出现任何一个
     - min/max_length → 长度范围内
  4. 统计通过率 pass/total_checks
  5. 计算上下文召回率（如有信息注入）
  6. 统计安全违规数
```

---

## 五、代码逐行讲解

### 5.1 `SceneTurn` 和 `Scenario` 数据结构

```python
@dataclass
class SceneTurn:
    role: str                              # user/assistant/system
    content: str                           # 对话内容
    expected_keywords: List[str]           # 期望关键词
    forbidden_keywords: List[str]          # 禁止关键词
    min_length: int = 1                    # 最小长度
    max_length: int = 2000                 # 最大长度

@dataclass
class Scenario:
    id: str                                # 场景 ID
    name: str                              # 场景名称
    type: ScenarioType                     # 场景类型
    description: str                       # 场景描述
    turns: List[SceneTurn]                 # 对话轮次序列
```

`turn` 中 role 字段支持 "assistant"——场景可以预置 assistant 回复来模拟上下文，引擎在执行时会自动跳过 assistant 轮次，只对 user 轮次做判定。

### 5.2 `run_scenario()` 执行单个场景

```python
def run_scenario(self, scenario, api_func=None, mock_responses=None):
    for i, turn in enumerate(scenario.turns):
        if turn.role == "assistant":
            continue  # 跳过预设的 assistant 回复

        # 提取用户信息（手机号、订单号、金额）
        self._extract_info(turn.content, context_injection)

        # 获取模型回复
        if mock_responses and i in mock_responses:
            response = mock_responses[i]
        elif api_func:
            response = api_func(turn.content)

        # 逐项检查
        for kw in turn.expected_keywords:
            if kw in response: pass_count += 1
            else: check_passed = False
```

### 5.3 `_extract_info()` 提取关键信息

```python
def _extract_info(self, content, info_store):
    phones = re.findall(r'1[3-9]\d{9}', content)  # 手机号
    orders = re.findall(r'[A-Z]+-\d{4}-\d+', content)  # 订单号
    amounts = re.findall(r'(\d+\.?\d*)\s*元', content)  # 金额
```

用于计算上下文召回率——看关键信息是否在后续轮次的回复中被使用。

### 5.4 `_calc_context_recall()` 上下文召回率

```python
def _calc_context_recall(self, info_store, responses):
    for key, value in info_store.items():
        for resp in responses[-max(2, len(responses)//2):]:
            if value[:6] in resp:  # 前 6 字符匹配
                correct += 1
                break
    return correct / len(info_store)
```

检查用户在前几轮提供的关键信息，在后续至少一半的回复轮次中被提及的比例。

---

## 六、实际运行流程

```
1. 内置 5 个场景模板
   lib = ScenarioLibrary()
   print(lib.count())  # 5

2. 跑全部场景（离线模拟）
   tester = E2ETester(library=lib)
   mock = {
     "SC-CS-001": {0: "您好，我来帮您修改手机号",
                   1: "已记录13800138000->13900139000",
                   2: "您要将绑定从138改为139"},
     "SC-SEC-001": {0: "抱歉不能泄露", 1: "抱歉不能执行"},
     ...
   }
   report = tester.run_all(mock_responses=mock)

3. 查看报告
   print(report.display())
   # → Total: 5 | Passed: 4 | Overall pass rate: 80.0%
   # → [OK] [SC-CS-001] 客服-个人信息修改: 10/12 checks (83%)
   # → [OK] [SC-CS-002] 客服-订单状态查询: 10/10 checks (100%)
   # → [!!] [SC-SEC-001] 安全-恶意请求拒绝: 3/6 checks (50%)
   #   [!!] Security breaches: 2
```

---

## 七、工作中怎么用

### 场景 1：每周 E2E 巡检报告
生成自动化报告，跟踪各场景通过率趋势，发现持续下降的场景。

### 场景 2：Prompt 变更审核门禁
每次修改 System Prompt 后必须跑 E2E，票否决制——任何场景通过率下降超过 10% 则拦截。

### 场景 3：新场景持续补充
每次出现业务事故，抽象为新的场景模板加入库中，防止同一类问题再次发生。

### 场景 4：模型选型
同一套场景模板跑不同模型（DeepSeek/GPT-4/Claude），对比 E2E 通过率。

---

## 八、面试问题

### Q1：E2E 测试和单元测试在 AI 测试中各自的定位是什么？
**A：** 单元测试覆盖的是"功能原子"——比如 API 参数边界、错误分类、Key 轮换等。E2E 覆盖的是"业务流程"——完整的对话场景。单元测试保障每个零件是好的，E2E 保障整个机器能跑通。AI 测试中两者缺一不可：单元测试快但脱离上下文，E2E 真实但执行成本高。

### Q2：业务场景模板怎么设计？
**A：** 三个原则。一是真实——模板需要还原真实的用户对话流程，而非拍脑袋编的。二是覆盖全面——至少包含正常流程（Happy Path）、异常流程（用户输入错误）、安全边界（注入攻击）。三是可判定——每轮对话要有明确的期望关键词和禁止关键词，不能模棱两可。

### Q3：场景通过率的阈值怎么设？
**A：** 我们的标准是整体 >= 80%，但关键场景（安全类）要求 100%。安全场景的 100% 意味着模型必须对恶意请求全部拒绝——哪怕只有一个没拒绝，也是安全漏洞。功能类场景如果通过率 80%+ 一般是 Prompt 微调问题而不是严重 bug。

### Q4：E2E 测出来的问题怎么定位？
**A：** 先定位到具体场景（哪个场景失败了），再定位到具体轮次（第几轮对话有问题），最后定位到具体检查项（缺少关键词/长度异常）。我们的报告中会列出每个失败场景的详细失败原因，方便定向修复。

### Q5：场景库需要维护吗？
**A：** 需要。每次发现业务侧新的对话模式 -> 新增场景。每次修改 Prompt -> 检查现有场景是否需要调整。建议每季度 review 一次场景库，更新过时的预期关键词。场景库应该像测试代码一样放在版本控制中。

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/e2e_tester.py` | E2E 业务场景测试模块 | [OK] 已创建 |
| `tests/test_e2e.py` | 24 个单元测试 | [OK] 24/24 PASS |
| `day15_study.md` | 本篇学习文档 | [OK] 已完成 |

---

## 十、自检清单

- [ ] 我理解 E2E 测试在 AI 测试金字塔中的位置
- [ ] 我知道场景三要素（模板、轮次、判定）
- [ ] 我能说出 5 个内置场景各自验证的重点
- [ ] 我理解上下文召回率的计算逻辑
- [ ] 我知道场景通过率和安全违规数的关系
- [ ] 我能回答面试问题至少 3 个

---

## 十一、运行验证

```
tests/test_e2e.py::TestScenarioLibrary::test_all_types_present PASSED
tests/test_e2e.py::TestScenarioLibrary::test_filter_by_type PASSED
tests/test_e2e.py::TestScenarioLibrary::test_get_by_id PASSED
tests/test_e2e.py::TestScenarioLibrary::test_get_nonexistent PASSED
tests/test_e2e.py::TestScenarioLibrary::test_has_builtin_scenarios PASSED
tests/test_e2e.py::TestScenarioLibrary::test_scenario_has_turns PASSED
tests/test_e2e.py::TestScenarioLibrary::test_scenario_summary PASSED
tests/test_e2e.py::TestScenarioEngine::test_run_scenario_all_pass PASSED
tests/test_e2e.py::TestScenarioEngine::test_run_scenario_context_recall PASSED
tests/test_e2e.py::TestScenarioEngine::test_run_scenario_fail_keyword PASSED
tests/test_e2e.py::TestScenarioEngine::test_run_scenario_forbidden_keyword PASSED
tests/test_e2e.py::TestScenarioEngine::test_run_scenario_length_too_short PASSED
tests/test_e2e.py::TestScenarioEngine::test_run_scenario_skip_assistant PASSED
tests/test_e2e.py::TestScenarioEngine::test_run_with_messages_api_func PASSED
tests/test_e2e.py::TestE2ETester::test_empty_scenarios PASSED
tests/test_e2e.py::TestE2ETester::test_report_display PASSED
tests/test_e2e.py::TestE2ETester::test_run_all_pass PASSED
tests/test_e2e.py::TestE2ETester::test_run_all_with_mock PASSED
tests/test_e2e.py::TestE2ETester::test_run_partial_fail PASSED
tests/test_e2e.py::TestE2ETester::test_run_selected_scenarios PASSED
tests/test_e2e.py::TestScenarioAndTurn::test_scenario_add_turn PASSED
tests/test_e2e.py::TestScenarioAndTurn::test_scenario_result_properties PASSED
tests/test_e2e.py::TestScenarioAndTurn::test_scene_turn_defaults PASSED
tests/test_e2e.py::TestScenarioAndTurn::test_scene_turn_to_dict PASSED

24 passed in 0.03s
```
