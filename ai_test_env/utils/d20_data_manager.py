"""
Day 20 (Week 4 Day 5) — 测试数据管理

功能：
1. PromptDataFactory — 合成 Prompt 数据生成器（模板替换 + 随机填充）
2. ResponseDataFactory — 合成 Response 数据生成器（有效 / 截断 / 拒绝 / 空回复）
3. DataProfile — 数据集配置（数量比例、字段映射、输出格式）
4. DataMasker — 脱敏工具（邮箱、手机号、身份证、API Key）
5. DataVersionTracker — 数据版本追踪

面试话术：
    "我负责管理测试数据集，用 DataFactory 按模板生成合成数据。
    数据有版本号管理，每次增删改都会记录 changelog。
    上线前用 DataMasker 做脱敏扫描，确保不把真实用户数据带到测试环境。"
"""
import os
import json
import hashlib
import random
import string
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# 数据配置文件
# ---------------------------------------------------------------------------

@dataclass
class DataProfile:
    """数据集配置"""
    name: str                               # 数据集名称
    count: int = 100                        # 生成数量
    output_format: str = "jsonl"            # jsonl / json / csv
    seed: int = 42                          # 随机种子
    version: str = "1.0.0"                  # 版本号
    categories: List[str] = field(default_factory=lambda: ["general"])
    prompt_template: str = "default"        # prompt 模板
    response_type_ratios: Dict[str, float] = field(default_factory=lambda: {
        "valid": 0.70,
        "truncated": 0.10,
        "rejected": 0.10,
        "empty": 0.05,
        "error": 0.05,
    })

    def validate(self) -> List[str]:
        """校验配置有效性"""
        errors = []
        if self.count <= 0:
            errors.append("count must be positive")
        total = sum(self.response_type_ratios.values())
        if abs(total - 1.0) > 0.01:
            errors.append(f"ratios sum to {total}, expected 1.0")
        return errors

    def adjust_ratios(self) -> None:
        """归一化比例（如果总和不为 1）"""
        total = sum(self.response_type_ratios.values())
        if total > 0:
            for k in self.response_type_ratios:
                self.response_type_ratios[k] /= total


# ---------------------------------------------------------------------------
# 合成 Prompt 数据工厂
# ---------------------------------------------------------------------------

class PromptDataFactory:
    """
    合成 Prompt 数据生成器

    支持模板替换、随机填充和分类定制。
    模板示例：
        "What is {topic}?"
        "Explain {concept} in {style} style"
        "Write a {length} {genre} about {subject}"
    """

    # 通用主题词库
    TOPICS = [
        "machine learning", "deep learning", "natural language processing",
        "computer vision", "reinforcement learning", "neural networks",
        "transformers", "attention mechanism", "backpropagation",
        "gradient descent", "convolution", "tokenization", "embedding",
        "fine-tuning", "prompt engineering", "chain of thought",
        "few-shot learning", "zero-shot learning", "transfer learning",
        "data augmentation", "regularization", "batch normalization",
        "dropout", "activation function", "loss function",
        "ChatGPT", "GPT-4", "Claude", "Gemini", "DeepSeek",
        "API testing", "unit testing", "integration testing",
        "regression testing", "smoke testing", "performance testing",
    ]

    CONCEPTS = [
        "machine learning", "encapsulation", "polymorphism",
        "dependency injection", "the Transformer architecture",
        "attention is all you need", "reinforcement learning",
        "test-driven development", "continuous integration",
        "model evaluation", "overfitting", "LLM hallucination",
    ]

    STYLES = [
        "beginner", "expert", "educational", "concise", "detailed",
    ]

    GENRES = [
        "poem", "story", "essay", "code snippet", "dialogue",
        "explanation", "summary", "analysis", "review",
    ]

    SUBJECTS = [
        "artificial intelligence", "software testing",
        "the future of work", "climate change",
        "a day in the life of a QA engineer",
    ]

    LENGTHS = ["short", "medium", "long"]

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_prompts(self, profile: DataProfile) -> List[Dict]:
        """
        按配置生成 Prompt 数据集。

        Returns:
            [{"id": str, "text": str, "category": str, "tags": List[str]}, ...]
        """
        self.rng = random.Random(profile.seed)
        prompts = []
        category_cycle = profile.categories

        for i in range(profile.count):
            category = category_cycle[i % len(category_cycle)]
            text = self._generate_single(category)
            prompt_id = f"prompt_{profile.version.replace('.', '_')}_{i:04d}"
            prompts.append({
                "id": prompt_id,
                "text": text,
                "category": category,
                "tags": [f"v{profile.version}", category],
                "template": profile.prompt_template,
            })

        return prompts

    def _generate_single(self, category: str) -> str:
        """生成单条 prompt"""
        template_type = self.rng.randint(0, 6)

        if template_type == 0:
            return f"What is {self.rng.choice(self.TOPICS)}?"
        elif template_type == 1:
            return f"Explain {self.rng.choice(self.CONCEPTS)} in {self.rng.choice(self.STYLES)} terms"
        elif template_type == 2:
            return f"Write a {self.rng.choice(self.LENGTHS)} {self.rng.choice(self.GENRES)} about {self.rng.choice(self.SUBJECTS)}"
        elif template_type == 3:
            topics = self.rng.sample(self.TOPICS, 2)
            return f"Compare and contrast {topics[0]} and {topics[1]}"
        elif template_type == 4:
            return f"Give me a step-by-step guide to {self.rng.choice(self.TOPICS)}"
        elif template_type == 5:
            return f"What are the pros and cons of {self.rng.choice(self.TOPICS)}?"
        else:
            return f"Define {self.rng.choice(self.TOPICS)}. Then give an example."


# ---------------------------------------------------------------------------
# 合成 Response 数据工厂
# ---------------------------------------------------------------------------

class ResponseDataFactory:
    """
    合成 Response 数据生成器

    根据 Profile 中的比例生成多种类型的回复：
    - valid: 正常有效回复
    - truncated: 截断回复
    - rejected: 拒绝回复（内容安全）
    - empty: 空回复
    - error: 错误信息
    """

    VALID_TEMPLATES = [
        "{topic} is a fundamental concept in modern AI. It involves...",
        "Sure! Here's an explanation of {topic}: ...",
        "Great question! {topic} refers to the process of...",
        "I'd be happy to explain {topic}. In simple terms,...",
        "Here's a detailed overview of {topic}: First,...",
    ]

    REJECTION_TEMPLATES = [
        "I'm sorry, but I cannot provide information about that topic.",
        "I appreciate your question, but I'm not able to answer that.",
        "I cannot fulfill this request as it may violate content policies.",
        "I'm designed to be helpful, harmless, and honest. I cannot...",
        "This request falls outside my guidelines. Let me know if...",
    ]

    ERROR_TEMPLATES = [
        "Error: Request timeout. Please try again.",
        "Internal server error. Unable to process request at this time.",
        "Rate limit exceeded. Please wait before sending another request.",
        "Authentication failed. Please check your API key.",
        "Invalid request format: missing required field 'messages'.",
    ]

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_responses(self, profile: DataProfile,
                           prompts: Optional[List[Dict]] = None) -> List[Dict]:
        """
        按配置生成 Response 数据集。

        Args:
            profile: 数据配置
            prompts: 对应的 prompt 列表（用于关联）

        Returns:
            [{"id": str, "prompt_id": str, "text": str,
              "type": str, "finish_reason": str}, ...]
        """
        self.rng = random.Random(profile.seed + 1)
        responses = []
        ratios = profile.response_type_ratios

        # 按比例分配类型
        response_types = []
        type_labels = list(ratios.keys())
        type_weights = [ratios[k] for k in type_labels]

        for i in range(profile.count):
            rtype = self.rng.choices(type_labels, weights=type_weights, k=1)[0]
            response_types.append(rtype)

        for i, rtype in enumerate(response_types):
            prompt_id = f"prompt_{profile.version.replace('.', '_')}_{i:04d}"
            if prompts and i < len(prompts):
                prompt_id = prompts[i]["id"]

            resp = self._generate(rtype, prompt_id)
            responses.append(resp)

        return responses

    def _generate(self, rtype: str, prompt_id: str) -> Dict:
        """生成单条 response"""
        base = {
            "id": f"resp_{prompt_id}",
            "prompt_id": prompt_id,
        }

        if rtype == "valid":
            topic = self.rng.choice(PromptDataFactory.TOPICS)
            template = self.rng.choice(self.VALID_TEMPLATES)
            base["text"] = template.format(topic=topic)
            base["type"] = "valid"
            base["finish_reason"] = "stop"
            base["tokens"] = self.rng.randint(50, 300)

        elif rtype == "truncated":
            topic = self.rng.choice(PromptDataFactory.TOPICS)
            template = self.rng.choice(self.VALID_TEMPLATES)
            truncated = template.format(topic=topic)[:self.rng.randint(10, 30)]
            base["text"] = truncated + "..."
            base["type"] = "truncated"
            base["finish_reason"] = "length"
            base["tokens"] = self.rng.randint(5, 30)

        elif rtype == "rejected":
            template = self.rng.choice(self.REJECTION_TEMPLATES)
            base["text"] = template
            base["type"] = "rejected"
            base["finish_reason"] = "content_filter"
            base["tokens"] = self.rng.randint(10, 30)

        elif rtype == "empty":
            base["text"] = ""
            base["type"] = "empty"
            base["finish_reason"] = "stop"
            base["tokens"] = 0

        else:  # error
            template = self.rng.choice(self.ERROR_TEMPLATES)
            base["text"] = template
            base["type"] = "error"
            base["finish_reason"] = "error"
            base["tokens"] = 0

        base["model"] = "deepseek-chat"
        return base


# ---------------------------------------------------------------------------
# 数据脱敏工具
# ---------------------------------------------------------------------------

class DataMasker:
    """
    数据脱敏工具

    支持：
    - 邮箱脱敏: user@example.com → u***@example.com
    - 手机号脱敏: 13812345678 → 138****5678
    - 身份证脱敏: 110101199001011234 → 110101********1234
    - API Key 脱敏: sk-abcdefghijklmnopqrst → sk-****************qrst
    - IP 脱敏: 192.168.1.1 → 192.168.*.*
    """

    EMAIL_RE = re.compile(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
    PHONE_RE = re.compile(r'(1[3-9]\d)\d{4}(\d{4})')
    ID_CARD_RE = re.compile(r'(\d{6})\d{8}(\d{4})')
    API_KEY_RE = re.compile(r'(sk-)[a-zA-Z0-9]{20,}')
    IP_RE = re.compile(r'(\d{1,3}\.\d{1,3})\.\d{1,3}\.\d{1,3}')

    @staticmethod
    def mask_email(text: str) -> str:
        """脱敏邮箱: u***@example.com"""
        def _replace(m: re.Match) -> str:
            local, domain = m.group(1), m.group(2)
            if len(local) >= 2:
                masked = local[0] + "*" * (len(local) - 1)
            else:
                masked = local + "*"
            return f"{masked}@{domain}"
        return DataMasker.EMAIL_RE.sub(_replace, text)

    @staticmethod
    def mask_phone(text: str) -> str:
        """脱敏手机号: 138****5678"""
        return DataMasker.PHONE_RE.sub(r'\1****\2', text)

    @staticmethod
    def mask_id_card(text: str) -> str:
        """脱敏身份证: 110101********1234"""
        return DataMasker.ID_CARD_RE.sub(r'\1********\2', text)

    @staticmethod
    def mask_api_key(text: str) -> str:
        """脱敏 API Key: sk-****************qrst"""
        def _replace(m: re.Match) -> str:
            prefix = m.group(1)
            key_body = m.group(0)[len(prefix):]
            if len(key_body) >= 4:
                return prefix + "*" * (len(key_body) - 4) + key_body[-4:]
            return prefix + "*" * len(key_body)
        return DataMasker.API_KEY_RE.sub(_replace, text)

    @staticmethod
    def mask_ip(text: str) -> str:
        """脱敏 IP: 192.168.*.*"""
        return DataMasker.IP_RE.sub(r'\1.*.*', text)

    @staticmethod
    def mask_all(text: str) -> str:
        """全部脱敏"""
        text = DataMasker.mask_email(text)
        text = DataMasker.mask_phone(text)
        text = DataMasker.mask_id_card(text)
        text = DataMasker.mask_api_key(text)
        text = DataMasker.mask_ip(text)
        return text

    @staticmethod
    def has_sensitive_data(text: str) -> Dict[str, bool]:
        """检测是否包含敏感数据"""
        return {
            "email": bool(DataMasker.EMAIL_RE.search(text)),
            "phone": bool(DataMasker.PHONE_RE.search(text)),
            "id_card": bool(DataMasker.ID_CARD_RE.search(text)),
            "api_key": bool(DataMasker.API_KEY_RE.search(text)),
            "ip": bool(DataMasker.IP_RE.search(text)),
        }


# ---------------------------------------------------------------------------
# 数据版本追踪
# ---------------------------------------------------------------------------

@dataclass
class DatasetEntry:
    """数据条目"""
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def checksum(self) -> str:
        """计算校验和"""
        return hashlib.md5(self.text.encode()).hexdigest()


@dataclass
class VersionEntry:
    """版本记录"""
    version: str
    timestamp: str
    count: int
    changes: List[str] = field(default_factory=list)
    checksums: Dict[str, str] = field(default_factory=dict)


class DataVersionTracker:
    """
    数据版本追踪器

    管理数据集的版本号、变更历史、校验和。
    支持版本间 diff 和回滚预览。
    """

    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.current_version = "0.0.1"
        self.entries: List[DatasetEntry] = []
        self.history: List[VersionEntry] = []

    def add_entries(self, entries: List[DatasetEntry],
                    change_desc: str = "Initial import") -> str:
        """
        添加数据集。

        Args:
            entries: 数据条目列表
            change_desc: 变更描述

        Returns:
            新版本号
        """
        self.entries = entries
        new_version = self._bump_version()

        version_entry = VersionEntry(
            version=new_version,
            timestamp=datetime.now().isoformat(),
            count=len(entries),
            changes=[change_desc],
            checksums={e.id: e.checksum() for e in entries},
        )

        self.history.append(version_entry)
        self.current_version = new_version
        return new_version

    def update_entries(self, entries: List[DatasetEntry],
                       change_desc: str = "Data update") -> str:
        """
        更新（替换）数据集。
        """
        old_checksums = {e.id: e.checksum() for e in self.entries}
        self.entries = entries
        new_version = self._bump_version()

        new_checksums = {e.id: e.checksum() for e in entries}

        # 计算变更
        changes = [change_desc]
        added = set(new_checksums.keys()) - set(old_checksums.keys())
        removed = set(old_checksums.keys()) - set(new_checksums.keys())
        modified = [
            k for k in new_checksums
            if k in old_checksums and new_checksums[k] != old_checksums[k]
        ]

        if added:
            changes.append(f"Added: {len(added)} entries")
        if removed:
            changes.append(f"Removed: {len(removed)} entries")
        if modified:
            changes.append(f"Modified: {len(modified)} entries")

        version_entry = VersionEntry(
            version=new_version,
            timestamp=datetime.now().isoformat(),
            count=len(entries),
            changes=changes,
            checksums=new_checksums,
        )

        self.history.append(version_entry)
        self.current_version = new_version
        return new_version

    def _bump_version(self) -> str:
        """自动递增版本号"""
        parts = self.current_version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)

    def get_diff(self, version_a: str,
                 version_b: str) -> Dict[str, List]:
        """
        比较两个版本的差异。

        Args:
            version_a: 旧版本
            version_b: 新版本

        Returns:
            {"added": [...], "removed": [...], "modified": [...]}
        """
        checksums_a = {}
        checksums_b = {}

        for v in self.history:
            if v.version == version_a:
                checksums_a = v.checksums
            if v.version == version_b:
                checksums_b = v.checksums

        added = list(set(checksums_b.keys()) - set(checksums_a.keys()))
        removed = list(set(checksums_a.keys()) - set(checksums_b.keys()))
        modified = [
            k for k in checksums_b
            if k in checksums_a and checksums_b[k] != checksums_a[k]
        ]

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
        }

    def get_version_history(self) -> List[Dict]:
        """获取版本历史"""
        return [
            {
                "version": v.version,
                "timestamp": v.timestamp,
                "count": v.count,
                "changes": v.changes,
            }
            for v in sorted(self.history, key=lambda x: x.version)
        ]
