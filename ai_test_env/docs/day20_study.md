# Day 20 — 测试数据管理

## 学习目标

1. **理解 DataProfile**：掌握数据配置协议（类型比例、种子一致性、版本号）
2. **掌握 PromptDataFactory**：熟练运用模板替换和随机填充生成测试 Prompt
3. **掌握 ResponseDataFactory**：理解多类型回复生成（valid/truncated/rejected/empty/error）
4. **掌握 DataMasker**：熟练使用 5 种敏感信息脱敏方式
5. **掌握 DataVersionTracker**：理解版本管理和 changelog diff

---

## 一、今日目标

> 学会管理 AI 测试中的数据集：合成数据生成、敏感信息脱敏、版本追踪。这是 Week 4（自动化框架+工具链）的最后一块拼图——没有好的测试数据，前面的分层、CI、覆盖率都是空中楼阁。

- 理解 DataProfile 配置模式（类型比例、种子一致性、版本号）
- 掌握 PromptDataFactory 模板替换和随机填充
- 掌握 ResponseDataFactory 的多类型回复生成
- 学会 DataMasker 的 5 种敏感信息脱敏方式
- 理解 DataVersionTracker 的版本管理和 changelog diff

---

## 二、DataProfile — 数据配置协议

### 2.1 配置定义

数据集的"配方"——它定义了生成什么、多少量、按什么比例：

```python
from utils.d20_data_manager import DataProfile, DataCategory

profile = DataProfile(
    name="injection_suite",
    count=100,
    seed=42,                               # 种子确保可重复
    version="2.1.0",
    categories=[
        DataCategory.SQL_INJECTION,
        DataCategory.XSS,
        DataCategory.PROMPT_LEAK,
    ],
    response_type_ratios={
        "valid": 0.70,       # 正常回复 70%
        "truncated": 0.10,   # 截断回复 10%
        "rejected": 0.10,    # 拒绝回复 10%
        "empty": 0.05,       # 空回复 5%
        "error": 0.05,       # 错误回复 5%
    },
)
```

### 2.2 关键设计理念

- **种子一致性**：相同 seed 生成完全一样的数据 → 跨版本测试可对比
- **版本号**：每次变更数据集务必 bump → 追踪依赖关系
- **类型比率校验**：`validate_ratios()` 确保所有比例加起来 = 1.0

---

## 三、PromptDataFactory — Prompt 合成生成

### 3.1 模板类型

| 类型 | 模板结构 | 示例输出 |
|------|---------|---------|
| definition | What is {topic}? | "What is machine learning?" |
| explanation | Explain {concept} in {style} terms | "Explain dependency injection in expert terms" |
| writing | Write a {length} {genre} about {subject} | "Write a short poem about AI testing" |
| comparison | Compare and contrast {A} and {B} | "Compare and contrast CNNs and RNNs" |
| steps | Step-by-step guide to {topic} | "Step-by-step guide to fine-tuning" |
| code | Write {lang} code to {task} | "Write Python code to sort a list" |
| analysis | Analyze {scenario} and provide {depth} insights | "Analyze this log file and provide deep insights" |

### 3.2 模板替换机制

```python
from utils.d20_data_manager import PromptDataFactory

factory = PromptDataFactory()

# 生成单条
prompt = factory.generate_one(prompt_type="definition", topic="deep learning")
# → "What is deep learning?"

# 批量生成（根据 profile 配置）
prompts = factory.generate_batch(profile)
# → ["What is regression testing?", ...] × count

# 获取种子池
factory.get_seed_pool()
# → {"topic": [...], "concept": [...], "subject": [...], ...}
```

### 3.3 随机填充规则

每个模板插槽（如 `{topic}`、`{style}`）从种子池中随机取值。种子池预置了 AI 测试领域的常用词汇：

- **topic**: "deep learning", "NLP", "sentiment analysis", "regression testing", ...
- **concept**: "dependency injection", "gradient descent", "overfitting", ...
- **style**: "simple", "expert", "layman", "technical", ...

---

## 四、ResponseDataFactory — 回复合成生成

### 4.1 回复类型

```python
from utils.d20_data_manager import ResponseDataFactory

rf = ResponseDataFactory()

# 有效
rf.generate_response("valid", prompt_text)
# → "Deep learning is a subset of machine learning..."

# 截断（通过截断 prompt 达到")
rf.generate_response("truncated", prompt_text)
# → "Deep learning is... [TRUNCATED]"

# 拒绝
rf.generate_response("rejected", prompt_text)
# → "I'm sorry, I cannot answer this question."

# 空
rf.generate_response("empty", prompt_text)
# → "" 或 "   "

# 错误
rf.generate_response("error", prompt_text)
# → "Traceback (most recent call last):\n  File ..."
```

### 4.2 按比例批量生成

```python
profile = DataProfile(
    name="demo", count=100, seed=42,
    categories=[DataCategory.GENERAL],
    response_type_ratios={
        "valid": 0.70, "truncated": 0.10,
        "rejected": 0.10, "empty": 0.05, "error": 0.05,
    },
)

responses = rf.generate_batch(
    profile=profile,
    prompts=[f"What is {t}?" for t in ["AI", "ML", "DL"]],
)
# → ~70% valid, ~10% each of truncated/rejected/empty/error
```

---

## 五、DataMasker — 敏感信息脱敏

### 5.1 5 种脱敏规则

| 类型 | 输入 | 输出 | 正则 |
|------|------|------|------|
| 邮箱 | `user@example.com` | `u***@example.com` | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` |
| 手机 | `13812345678` | `138****5678` | `1[3-9]\d{9}` |
| 身份证 | `110101199001011234` | `110101********1234` | `\d{17}[\dXx]` |
| API Key | `sk-abcdefghijklmnopqrst` | `sk-****************qrst` | `sk-[a-zA-Z0-9]{20,}` |
| IP | `192.168.1.1` | `192.168.*.*` | `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}` |

### 5.2 使用

```python
from utils.d20_data_manager import DataMasker

masker = DataMasker()

# 单个字段脱敏
print(masker.mask_phone("13812345678"))
# → "138****5678"

print(masker.mask_email("user@example.com"))
# → "u***@example.com"

# 全文扫描脱敏
text = "Contact user@example.com or call 13812345678"
print(masker.mask_all(text))
# → "Contact u***@example.com or call 138****5678"

# 敏感信息检测
print(masker.has_sensitive_data("My API key is sk-test1234567890abcdef"))
# → True
```

### 5.3 注意事项

- **部分脱敏**：手机号 `"1381234"`（不足 11 位）→ 跳过，`mask_phone` 返回原文
- **API Key 长度校验**：`sk-` 后必须 20+ 字符才匹配，避免误伤 `sk-test`
- **双重校验**：`has_sensitive_data` 走宽松正则，`mask_all` 走严格正则做双重验证

---

## 六、DataVersionTracker — 版本追踪

### 6.1 版本管理流程

```
v0.0.1 ── add_entries("Initial import") ──→ v0.0.2
                                            │
                                      update_entries("Fix typos")
                                            │
                                            v
                                         v0.0.3 ── ... → v0.0.4
```

版本号格式：`{major}.{minor}.{patch}`

### 6.2 使用

```python
from utils.d20_data_manager import DataVersionTracker

tracker = DataVersionTracker()

# 初始化
assert tracker.current_version == "0.0.1"

# 新增
tracker.add_entries("Initial import of injection dataset")

# 更新（自动 bump patch）
tracker.update_entries("Fix typos in 50 cases")
tracker.update_entries("Add 50 Chinese test cases")
# → v0.0.4

# 查看 diff
diffs = tracker.get_diff(v1="0.0.1", v2="0.0.4")
# → {"v0.0.1": {"added": 20}, "v0.0.2": {"modified": 50}, ...}

# 版本历史
history = tracker.get_version_history()
# → [
#   {"version": "0.0.1", "action": "init", ...},
#   {"version": "0.0.2", "action": "add_entry", "message": "Initial import", ...},
#   ...
# ]
```

### 6.3 Diff 追踪的内容

| 变更类型 | 含义 | 触发操作 |
|---------|------|---------|
| added | 新增条目 | `add_entries()` |
| modified | 修改条目（带 checksum 验证） | `update_entries()` |
| checksum | 数据完整性校验 | 每版自动计算 |

Checksum 用于验证数据是否被篡改——发布版本后的非受控修改会导致 checksum 不匹配。

---

## 七、完整使用示例

### 7.1 生成 + 脱敏 + 版本追踪

```python
from utils.d20_data_manager import (
    DataProfile, DataCategory,
    PromptDataFactory, DataMasker, DataVersionTracker,
)

# 1. 配置
profile = DataProfile(
    name="production_suite", count=50, seed=42,
    categories=[DataCategory.GENERAL, DataCategory.SQL_INJECTION],
)

# 2. 生成 prompt
factory = PromptDataFactory()
prompts = factory.generate_batch(profile)

# 3. 脱敏（如果在 prompt 中有敏感信息）
masker = DataMasker()
cleaned = [masker.mask_all(p) for p in prompts]

# 4. 版本管理
tracker = DataVersionTracker()
tracker.add_entries(f"Generated {len(cleaned)} prompts")
```

### 7.2 脱敏测试前后的对比

```python
from utils.d20_data_manager import DataMasker

masker = DataMasker()

test_cases = [
    ("user@evil.com", True, "邮箱未脱敏"),
    ("13800138000", True, "手机号未脱敏"),
    ("sk-abcd1234567890abcdef1234567890", True, "API Key 未脱敏"),
    ("这是一个普通文本", False, "正常文本误判断"),
]

for text, should_be_sensitive, msg in test_cases:
    assert masker.has_sensitive_data(text) == should_be_sensitive, msg
```

---

## 八、面试话术

> "我设计了一套完整的测试数据管理体系。PromptDataFactory 用模板+种子池批量生成可重复的测试 Prompt，ResponseDataFactory 能按比例生成 valid/truncated/rejected/empty/error 五种响应类型——这让我们能构造边缘场景。DataMasker 在上线前自动扫描并脱敏 5 种敏感信息（邮箱、手机、身份证、API Key、IP），全量上线前必须确认 has_sensitive_data 返回 False。DataVersionTracker 给每个数据集打版本号，自动做 diff，防止数据污染影响回归测试结果。这三层合在一起，保证了测试数据的一致性、安全性和可追溯性。"

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d20_data_manager.py` | 数据管理模块 | [OK] |
| `tests/d20_test_data_manager.py` | 42 个测试 | [OK] 42/42 PASS |
| `day20_study.md` | 本文档 | [OK] 已升级 |

**学习检查点**：
- [ ] 会定义 DataProfile 配置并理解各字段作用
- [ ] 能说明种子（seed）在数据生成中的作用
- [ ] 会用 PromptDataFactory 生成指定类型的 prompt
- [ ] 知道 5 种脱敏规则和各自的适用场景
- [ ] 会追踪数据集版本、查看 diff 和 changelog
- [ ] 理解 checksum 在数据完整性中的作用

---

## 面试题

### 面试题 1：如何设计一个可重复的测试数据生成系统？

**答案：**

设计可重复的测试数据生成系统需要考虑种子机制、模板系统和版本控制：

**1. 种子机制（Seed）**
- 相同种子生成完全相同的数据
- 确保跨版本测试可对比
- 支持随机性和确定性的平衡

```python
import random

class SeededRandom:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
    
    def choice(self, seq):
        return self.rng.choice(seq)
    
    def sample(self, seq, k):
        return self.rng.sample(seq, k)
```

**2. 模板系统**
- 模板类型：definition、explanation、writing、comparison、steps、code、analysis
- 插槽填充：从种子池中随机取值
- 支持批量生成

**3. 配置管理**
```python
profile = DataProfile(
    name="test_suite",
    count=100,
    seed=42,
    version="1.0.0",
    categories=[DataCategory.SQL_INJECTION, DataCategory.XSS]
)
```

**4. 版本控制**
- 版本号格式：major.minor.patch
- 变更记录：added、modified、checksum
- 支持版本对比和回滚

### 面试题 2：测试数据脱敏的最佳实践是什么？

**答案：**

测试数据脱敏是保护用户隐私的重要措施：

**1. 脱敏规则矩阵**

| 类型 | 模式 | 替换格式 | 适用场景 |
|------|------|---------|---------|
| 邮箱 | `***@domain.com` | `***@domain.com` | 日志、报告 |
| 手机号 | `138****5678` | 中间4位脱敏 | 测试数据 |
| 身份证 | `310***1234` | 前3后4脱敏 | 金融场景 |
| API Key | `sk-***` | 前缀保留 | 安全测试 |
| IP 地址 | `10.***.***.100` | 网段保留 | 网络测试 |

**2. 脱敏时机**
- **生成时脱敏**：数据生成阶段直接脱敏
- **使用前脱敏**：在数据使用前统一处理
- **输出时脱敏**：在日志/报告中脱敏

**3. 验证流程**
```python
# 脱敏后必须验证
assert not masker.has_sensitive_data(sanitized_text)
assert masker.has_sensitive_data(original_text)  # 原始数据应该被识别
```

**4. 注意事项**
- 保留数据格式特征用于测试
- 脱敏后数据仍需可用
- 防止重标识攻击

---

## 代码示例

### 测试数据管理器实现

```python
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import hashlib
import random

class DataCategory(Enum):
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PROMPT_LEAK = "prompt_leak"
    NORMAL = "normal"

class ResponseType(Enum):
    VALID = "valid"
    TRUNCATED = "truncated"
    REJECTED = "rejected"
    EMPTY = "empty"
    ERROR = "error"

@dataclass
class DataProfile:
    name: str
    count: int
    seed: int = 42
    version: str = "1.0.0"
    categories: List[DataCategory] = field(default_factory=list)
    response_type_ratios: Dict[str, float] = field(default_factory=lambda: {
        "valid": 0.70,
        "truncated": 0.10,
        "rejected": 0.10,
        "empty": 0.05,
        "error": 0.05
    })

class PromptDataFactory:
    """Prompt 数据工厂"""
    
    TEMPLATES = {
        "definition": "What is {topic}?",
        "explanation": "Explain {concept} in {style} terms",
        "writing": "Write a {length} {genre} about {subject}",
        "comparison": "Compare and contrast {A} and {B}",
        "steps": "Step-by-step guide to {topic}",
        "code": "Write {lang} code to {task}",
        "analysis": "Analyze {scenario} and provide {depth} insights"
    }
    
    SEED_POOLS = {
        "topic": ["deep learning", "NLP", "regression testing", "CI/CD", "Docker"],
        "concept": ["gradient descent", "overfitting", "dependency injection", "microservices"],
        "style": ["simple", "expert", "layman", "technical"],
        "length": ["short", "medium", "long"],
        "genre": ["poem", "essay", "report", "email"],
        "subject": ["AI testing", "machine learning", "software quality", "DevOps"],
        "A": ["CNNs", "RNNs", "Transformers", "BERT"],
        "B": ["LSTMs", "GRUs", "ResNet", "GPT"],
        "lang": ["Python", "JavaScript", "Go", "Rust"],
        "task": ["sort a list", "implement a queue", "parse JSON", "connect to DB"],
        "scenario": ["this log file", "the user feedback", "the system metrics", "the error report"],
        "depth": ["shallow", "moderate", "deep", "comprehensive"]
    }
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
    
    def _fill_slot(self, slot: str) -> str:
        pool = self.SEED_POOLS.get(slot, [])
        if not pool:
            return slot
        return self.rng.choice(pool)
    
    def _fill_template(self, template: str) -> str:
        result = template
        for match in re.finditer(r'\{(\w+)\}', template):
            slot = match.group(1)
            value = self._fill_slot(slot)
            result = result.replace(f"{{{slot}}}", value)
        return result
    
    def generate_one(self, prompt_type: str, **kwargs) -> str:
        template = self.TEMPLATES.get(prompt_type, "{topic}")
        for key, value in kwargs.items():
            template = template.replace(f"{{{key}}}", str(value))
        return self._fill_template(template)
    
    def generate_batch(self, profile: DataProfile) -> List[str]:
        results = []
        for _ in range(profile.count):
            prompt_type = self.rng.choice(list(self.TEMPLATES.keys()))
            results.append(self.generate_one(prompt_type))
        return results

class ResponseDataFactory:
    """响应数据工厂"""
    
    RESPONSES = {
        ResponseType.VALID: [
            "这是一个有效的回复，包含了所需的信息。",
            "根据您的要求，我提供了详细的分析和解答。"
        ],
        ResponseType.TRUNCATED: [
            "由于字数限制，回复被截断...",
            "未完成的回复内容"
        ],
        ResponseType.REJECTED: [
            "抱歉，我无法满足这个请求。",
            "对不起，这个问题我无法回答。"
        ],
        ResponseType.EMPTY: ["", "   "],
        ResponseType.ERROR: [
            "发生错误：服务暂时不可用。",
            "系统错误，请稍后重试。"
        ]
    }
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
    
    def generate_one(self, response_type: ResponseType) -> str:
        responses = self.RESPONSES.get(response_type, [])
        return self.rng.choice(responses) if responses else ""
    
    def generate_by_ratios(self, ratios: Dict[str, float]) -> Tuple[ResponseType, str]:
        roll = self.rng.random()
        cumulative = 0.0
        for rt_name, ratio in ratios.items():
            cumulative += ratio
            if roll <= cumulative:
                rt = ResponseType(rt_name)
                return rt, self.generate_one(rt)
        return ResponseType.VALID, self.generate_one(ResponseType.VALID)

class DataMasker:
    """数据脱敏器"""
    
    PATTERNS = {
        "email": (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', 
                  lambda m: m.group(0)[:3] + '***' + m.group(0)[m.group(0).find('@'):]),
        "phone": (r'1[3-9]\d{9}', 
                  lambda m: m.group(0)[:3] + '****' + m.group(0)[7:]),
        "id_card": (r'\d{17}[\dXx]', 
                    lambda m: m.group(0)[:3] + '****' + m.group(0)[14:]),
        "api_key": (r'sk-[a-zA-Z0-9]{20,}', 
                    lambda m: 'sk-***'),
        "ip": (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 
               lambda m: m.group(0).split('.')[0] + '.***.***.' + m.group(0).split('.')[-1])
    }
    
    def mask(self, text: str) -> str:
        result = text
        for pattern_name, (regex, replacer) in self.PATTERNS.items():
            result = re.sub(regex, replacer, result)
        return result
    
    def has_sensitive_data(self, text: str) -> bool:
        for pattern_name, (regex, _) in self.PATTERNS.items():
            if re.search(regex, text):
                return True
        return False

class DataVersionTracker:
    """数据版本追踪器"""
    
    def __init__(self):
        self.current_version = "0.0.1"
        self.changelog: Dict[str, Dict] = {}
        self._init_version()
    
    def _init_version(self):
        self.changelog[self.current_version] = {
            "action": "init",
            "message": "Initial version",
            "added": 0,
            "modified": 0,
            "checksum": self._compute_checksum("")
        }
    
    def _compute_checksum(self, data: str) -> str:
        return hashlib.md5(data.encode()).hexdigest()[:8]
    
    def _bump_version(self, level: str = "patch"):
        parts = self.current_version.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        if level == "major":
            major += 1
            minor = 0
            patch = 0
        elif level == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
        self.current_version = f"{major}.{minor}.{patch}"
    
    def add_entries(self, message: str, count: int = 1):
        self._bump_version("patch")
        self.changelog[self.current_version] = {
            "action": "add_entry",
            "message": message,
            "added": count,
            "modified": 0,
            "checksum": self._compute_checksum(message)
        }
    
    def update_entries(self, message: str, count: int = 1):
        self._bump_version("patch")
        self.changelog[self.current_version] = {
            "action": "update_entry",
            "message": message,
            "added": 0,
            "modified": count,
            "checksum": self._compute_checksum(message)
        }
    
    def get_diff(self, v1: str, v2: str) -> Dict:
        result = {}
        for version in sorted(self.changelog.keys()):
            if version > v1 and version <= v2:
                result[version] = self.changelog[version]
        return result
    
    def get_version_history(self) -> List[Dict]:
        return [
            {"version": v, **data}
            for v, data in sorted(self.changelog.items())
        ]

# 使用示例
# 1. 生成 Prompt 数据
factory = PromptDataFactory(seed=42)
prompt = factory.generate_one("definition", topic="deep learning")
print(f"Prompt: {prompt}")

# 2. 生成批量数据
profile = DataProfile(name="test", count=5, seed=42)
prompts = factory.generate_batch(profile)
print(f"Batch: {len(prompts)} prompts")

# 3. 生成响应数据
resp_factory = ResponseDataFactory(seed=42)
response_type, response = resp_factory.generate_by_ratios(profile.response_type_ratios)
print(f"Response type: {response_type.value}, content: {response[:20]}")

# 4. 数据脱敏
masker = DataMasker()
test_text = "用户邮箱: test@example.com, 手机: 13812345678"
sanitized = masker.mask(test_text)
print(f"Original: {test_text}")
print(f"Sanitized: {sanitized}")
print(f"Has sensitive: {masker.has_sensitive_data(test_text)}")

# 5. 版本追踪
tracker = DataVersionTracker()
tracker.add_entries("Added 100 SQL injection cases", 100)
tracker.update_entries("Fixed typos", 50)
print(f"Current version: {tracker.current_version}")
print(f"History: {tracker.get_version_history()}")
```

---

## 练习题

### 练习题 1：实现数据质量评分系统

**要求：**
实现一个数据质量评分系统，评估测试数据的多维度质量。

**步骤：**
1. 定义质量维度（多样性、覆盖率、平衡性）
2. 实现各维度评分计算
3. 计算综合质量分数
4. 生成质量报告和改进建议

### 练习题 2：实现数据对比工具

**要求：**
实现一个数据集对比工具，支持版本间的数据差异分析。

**步骤：**
1. 实现数据条目比对算法
2. 识别新增、删除、修改的条目
3. 生成详细的 diff 报告
4. 支持可视化对比

### 练习题 3：实现自动化数据清洗管道

**要求：**
实现一个自动化的测试数据清洗管道。

**步骤：**
1. 设计清洗规则配置
2. 实现数据读取和解析
3. 执行脱敏和格式标准化
4. 生成清洗报告和统计

---
