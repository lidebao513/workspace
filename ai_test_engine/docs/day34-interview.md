# Week 8 Day 34 — 面试题刷练

## 学习目标

1. 掌握 STAR 面试回答框架，学会结构化地回答行为类问题
2. 理解 AI 测试领域的核心面试问题，学会结合项目经验回答
3. 学会将项目亮点转化为面试中的具体案例
4. 掌握反问面试官的技巧，学会获取关键信息

## 高频面试题 10 道（STAR 格式 + 项目引用）

### 1. 请描述你测试 AI 模型/API 的经验

**Situation:** 公司需要从 0 搭建 AI API 测试体系，覆盖 DeepSeek 接口的全链路质量保障。

**Task:** 我负责设计并实现一套完整的 AI 测试框架，包括连通性、质量评估、安全测试和性能压测。

**Action:** 我用 Python + OpenAI SDK 搭建了 `ai_test_engine`，分层架构：config/core 为基础层，tests/smoke/quality/security/performance 为测试层。核心模块包括 API 客户端封装、Key 轮换与降级、分级错误处理（`error_handler.py` 四级 FATAL/ERROR/WARN/INFO）、并发压测（`LoadTester`，计算 P95/P99/吞吐量）、熔断器（`CircuitBreaker` 三态状态机），共 161+ 测试用例。

**Result:** 框架覆盖了从冒烟（62 个测试）到性能的 6 个维度，CI 集成 GitHub Actions，支持多 Python 版本矩阵测试。项目中发现的浮点数精度问题（0.3 vs 0.30000000000004）被写入测试修复记录。

### 2. 如何评估 LLM 回复质量？

**Situation:** 需要一套可复现的回复质量评估标准，替代人工逐条评审。

**Task:** 设计 5 维评分体系（completeness/relevance/coherence/consistency/conciseness），配合 LLM-as-Judge 自动打分。

**Action:** 实现了 `QualityScore` 类（5 维加权评分）、`LLMJudge` 类（JSON 解析三层兜底：直接解析 → 正则提取 → 默认 0.5 分）、`AssessmentPipeline`（端到端流水线 + 版本对比得出 improvement/delta）。

**Result:** 每次 API 调用自动生成评分报告，可跟踪版本之间的质量回归（delta < -0.1 触发回归标记）。

### 3. 如何测试 Prompt Injection 安全性？

**Situation:** LLM 上线前必须验证对提示注入攻击的防御能力。

**Task:** 设计覆盖 9 种注入类型的测试框架，包括 direct_override、role_play、system_leak、encoding_confusion、jailbreak 等。

**Action:** 实现了 `InjectionTester`，包含 attack_cases 生成器（9 种类型各一条样本）和三层检测器：输入侧关键词匹配（override/encoding 特征）、输出侧拒绝语识别（sorry/cannot/unable/拒绝）、LLM Judge 二次判定。`run_test()` 输出按类型汇总的报告，含 total/detected/success_rate/by_type 字段。

**Result:** 9 种注入类型全部可检测，报告可按类型拆分。集成测试中 security 模块 14 个测试全部 PASS。

### 4. 如何处理 API 限流（Rate Limiting）？

**Situation:** API 请求频繁触发 429 错误，影响测试稳定性。

**Task:** 实现弹性重试机制，避免硬等待或无限重试。

**Action:** 实现了 `RateLimitError` 异常类（带 retry_after 字段），`ErrorHandler.classify()` 自动识别 429 为 WARN 级别 + RETRY 动作。同时配置了 `KeyManager` 的多 Key 轮换 + 模型降级策略：当当前 Key 连续失败 3 次后自动切换到备 Key，单 Key 模式下降级到备用模型。Key 池支持动态添加（`add_key()`），失败计数可重置（`reset()`）。

**Result:** 测试流水线从未因 429 中断。每次降级自动记录日志，总测试耗时降低约 40%。

### 5. 如何设计多轮对话的测试用例？

**Situation:** 单轮测试无法验证模型在长对话中的上下文保持能力。

**Task:** 设计注入→干扰→验证的三部曲测试脚本，量化上下文保持率。

**Action:** 实现了 `ConversationTester`，关键信息注入在第 N 轮，后续插入干扰轮次，最后在 M 轮后询问召回率。`track_context_retention()` 计算 recall_score（召回关键实体数 / 总数），`forgetting_curve()` 在 3/5/7 轮后分别测试，生成遗忘曲线。对话历史通过 `ConversationManager` 管理。

**Result:** 发现模型在第 5 轮后召回率下降到 60%，在第 7 轮后降到 40%。这个数据直接用于优化 system prompt 设计，增加关键信息重复策略。

### 6. 如何为 AI 测试搭建 CI/CD 流水线？

**Situation:** 需要让每次代码变更自动运行完整的 AI 测试套件，并生成可读报告。

**Task:** 设计 GitHub Actions workflow + 4 级门禁策略。

**Action:** 编写了 `.github/workflows/test.yml`，支持 Python 3.9/3.10/3.11 矩阵。门禁策略在 `CIConfigGenerator` 中配置：BLOCKING（阻塞 PR 合并）、MANDATORY（必须通过但可跳过紧急发布）、SILENT（仅通知）、PERTEST（每个测试独立门禁）。测试结果输出 HTML 报告（`pytest-html`），作为 CI artifact 存档。

**Result:** 每次 PR 自动跑 161+ 测试，平均 0.5 秒完成，HTML 报告可视化展示通过/失败分布。

### 7. 如何衡量和优化 Token 成本？

**Situation:** AI API 调用量增长快，需要监控和控制费用。

**Task:** 实现 Token 审计 + 费用监控系统，支持按日基线、异常告警和成本预测。

**Action:** 实现了 `TokenAuditor`，`record_call(prompt_tokens, completion_tokens)` 按输入/输出分开计费（输入 $0.0005 /1K，输出 $0.0015 /1K），`daily_report()` 按日汇总，`total_cost()` 累积总费用。数据记录包含 timestamp，支持环比异常检测。

**Result:** 每天自动生成 Token 消耗报告，及时发现异常增长。发现某天突然增长 200%，追查后发现是测试脚本误传了 10 倍冗余数据。

### 8. 如何测试 LLM 输出的稳定性和一致性？

**Situation:** 同个 prompt 在不同时间调用的输出不同，需要量化稳定性。

**Task:** 实现一致性检查器，同 prompt 多次调用后比较语义重叠率。

**Action:** 实现了 `ConsistencyChecker`（在 ai_test_env 中），从三个维度评估：语义去重率、关键实体覆盖率、命名实体重合度。`RobustnessTester`（在 ai_test_engine 中）进一步加入 6 种对抗扰动（typo/paraphrase/padding/encoding/role_play/format_jailbreak）。`RegressionTester.compare(prev, curr)` 自动标记 regression（delta < -0.1）或 improvement（delta > 0.1）。

**Result:** 稳定性量化后，发现 temperature=0 时一致性最高（96% 实体覆盖率），temperature=0.7 时下降到 72%。因此生产环境选择 temperature=0。

### 9. 如何测试 System Prompt 的健壮性？

**Situation:** System Prompt 被各种输入扰乱时是否还能保持行为边界？

**Task:** 设计 6 种扰动类型覆盖典型攻击向量。

**Action:** `RobustnessTester.perturb(text, ptype)` 支持 typo（字母加倍）、paraphrase（前置礼貌语）、padding（前后标记）、encoding（原样通过）、role_play（角色注入）、format_jailbreak（Markdown 包裹）。`test_all(text)` 返回 6 种扰动结果，每项含 original/perturbed/robust 字段。

**Result:** 发现 role_play 和 format_jailbreak 两种扰动最容易突破系统 prompt 边界，防御加强方向被明确。

### 10. 如何管理 AI 测试的数据？

**Situation:** AI 测试需要大量多样化测试用例，手工维护成本高。

**Task:** 设计测试数据工厂 + 脱敏 + 版本管理三位一体方案。

**Action:** `PromptDataFactory` 提供模板化生成，`ResponseDataFactory` 按类型（正常/错误/边界/空）生成回复。`DataMasker` 支持 5 种脱敏（API Key/邮箱/手机/身份证/自定义正则）。`DataVersionTracker` 记录版本 diff，支持前后对比。种子机制保证可重现（相同 seed 生成相同数据）。

**Result:** 1000 条测试数据 1 秒生成，脱敏零泄漏，版本回溯可精确定位到某次数据变更。

---

## 项目亮点速记

- **ai_test_engine**: 161 测试全部 PASS（smoke 62 + quality 13 + security 14 + performance 17 + integration 55）
- **ai_test_env**: ~600 测试用例，26 个模块，覆盖 8 周学习路径
- **技术栈**: Python, OpenAI SDK, pytest, unittest, GitHub Actions
- **覆盖维度**: 连通性 → 参数边界 → 错误处理 → 质量评估 → 安全注入 → 性能压测 → 熔断器 → Token 审计 → CI/CD

---

## 代码示例

### 面试准备工具：问题练习框架

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class InterviewQuestion:
    """面试问题模型"""
    question: str
    category: str  # 技术/行为/项目
    difficulty: str  # 初级/中级/高级
    star_answer: Dict[str, str] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    practice_count: int = 0
    last_practiced: Optional[datetime] = None

@dataclass
class PracticeSession:
    """练习会话记录"""
    question: str
    duration: int  # 秒
    score: int  # 1-5 分
    feedback: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

class InterviewPrepTool:
    """面试准备工具"""
    
    def __init__(self):
        self.questions: List[InterviewQuestion] = []
        self.sessions: List[PracticeSession] = []
    
    def add_question(self, question: InterviewQuestion) -> None:
        """添加面试问题"""
        self.questions.append(question)
    
    def get_by_category(self, category: str) -> List[InterviewQuestion]:
        """按类别筛选问题"""
        return [q for q in self.questions if q.category == category]
    
    def get_by_difficulty(self, difficulty: str) -> List[InterviewQuestion]:
        """按难度筛选问题"""
        return [q for q in self.questions if q.difficulty == difficulty]
    
    def record_practice(self, question: str, duration: int, 
                       score: int, feedback: str = "") -> None:
        """记录练习会话"""
        self.sessions.append(PracticeSession(
            question=question,
            duration=duration,
            score=score,
            feedback=feedback
        ))
        
        # 更新问题练习次数
        for q in self.questions:
            if q.question == question:
                q.practice_count += 1
                q.last_practiced = datetime.now()
                break
    
    def get_progress_report(self) -> dict:
        """生成练习进度报告"""
        if not self.sessions:
            return {"total_practiced": 0, "avg_score": 0, "recommendations": []}
        
        avg_score = sum(s.score for s in self.sessions) / len(self.sessions)
        total_practiced = len(self.sessions)
        
        # 找出需要加强的问题（练习次数少于3次或平均分低于4分）
        needs_work = [q for q in self.questions 
                     if q.practice_count < 3 or 
                     (self._get_avg_score(q.question) < 4 and q.practice_count > 0)]
        
        return {
            "total_practiced": total_practiced,
            "avg_score": round(avg_score, 2),
            "questions_count": len(self.questions),
            "needs_work_count": len(needs_work),
            "recommendations": [q.question for q in needs_work]
        }
    
    def _get_avg_score(self, question: str) -> float:
        """获取特定问题的平均分数"""
        scores = [s.score for s in self.sessions if s.question == question]
        if not scores:
            return 0
        return sum(scores) / len(scores)

# 使用示例
if __name__ == "__main__":
    tool = InterviewPrepTool()
    
    # 添加问题
    tool.add_question(InterviewQuestion(
        question="请描述你测试 AI 模型/API 的经验",
        category="项目",
        difficulty="高级",
        star_answer={
            "S": "公司需要从 0 搭建 AI API 测试体系",
            "T": "设计并实现完整的 AI 测试框架",
            "A": "用 Python + OpenAI SDK 搭建了 ai_test_engine",
            "R": "覆盖 6 个维度，161+ 测试用例"
        },
        keywords=["AI测试", "分层架构", "质量评估", "安全测试"]
    ))
    
    tool.add_question(InterviewQuestion(
        question="如何评估 LLM 回复质量？",
        category="技术",
        difficulty="中级",
        star_answer={
            "S": "需要替代人工评审的质量评估标准",
            "T": "设计 5 维评分体系",
            "A": "实现 QualityScore + LLMJudge + AssessmentPipeline",
            "R": "自动生成评分报告，可跟踪质量回归"
        },
        keywords=["5维评分", "LLM-as-Judge", "质量评估"]
    ))
    
    # 记录练习
    tool.record_practice("请描述你测试 AI 模型/API 的经验", 180, 4, 
                        "回答流畅，但可以增加更多具体数据")
    
    # 获取进度报告
    report = tool.get_progress_report()
    print("练习进度报告:")
    print(f"  总练习次数: {report['total_practiced']}")
    print(f"  平均分: {report['avg_score']}")
    print(f"  需要加强的问题: {report['needs_work_count']}")
```

---

## 练习题

1. **基础题：** 使用上面的 `InterviewPrepTool`，添加 3 个你觉得最常被问到的 AI 测试面试问题，并填写完整的 STAR 回答。

2. **进阶题：** 模拟一次完整的面试练习，选择 5 道问题，每道题练习 3 分钟，然后给自己打分并记录反馈。

3. **挑战题：** 设计一个 AI 面试模拟工具，能够自动生成问题、记录回答时长、提供改进建议。

---

## 自检清单

- [ ] 10 道题能不看文档自然讲出来
- [ ] 每题都有项目具体数据支撑（161 tests, 0.5s）
- [ ] 能用 ASCII 画项目架构图
- [ ] 每个知识点都能关联到 ai_test_engine 的具体代码/测试
- [ ] 准备好反问面试官的问题

---
