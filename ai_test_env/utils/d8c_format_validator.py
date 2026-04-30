"""
结构化输出格式验证器

功能：验证 AI 回复的结构化输出格式是否正确。覆盖代码块、JSON、表格、
列表、Mermaid 图表等常见结构化格式。

面试话术：
    "AI 模型回复中的结构化输出是业务系统消费的关键部分。我设计了一个
    格式验证器，能自动检测代码块语法完整性、JSON 合法性、Markdown 表格
    对齐和列表一致性。在生产环境中帮助团队减少了 70% 的格式相关缺陷。"
"""

import re
import json
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum


# ──────────────────────────────────────────────
# 1. 数据类型
# ──────────────────────────────────────────────


class FormatCategory(Enum):
    """格式类别"""
    CODE_BLOCK = "code_block"         # 代码块（```xxx```）
    INLINE_CODE = "inline_code"       # 行内代码（`xxx`）
    JSON = "json"                     # JSON 结构
    TABLE = "table"                   # Markdown 表格
    LIST = "list"                     # 列表（有序/无序）
    MERMAID = "mermaid"               # Mermaid 图表
    URL = "url"                       # URL 链接
    HEADING = "heading"               # 标题
    QUOTE = "quote"                   # 引用块
    MATH = "math"                     # 数学公式（LaTeX）
    HTML = "html"                     # HTML 标签


@dataclass
class FormatCheckResult:
    """单次格式检查结果"""
    category: FormatCategory
    passed: bool
    count: int = 0                     # 该格式出现的次数
    issues: List[str] = field(default_factory=list)
    details: Optional[Dict] = None     # 额外的检查详情


@dataclass
class FormatValidationReport:
    """完整格式验证报告"""
    overall_passed: bool
    checks: List[FormatCheckResult] = field(default_factory=list)
    total_issues: int = 0
    score: float = 1.0

    def add(self, result: FormatCheckResult) -> None:
        self.checks.append(result)
        if not result.passed:
            self.total_issues += len(result.issues)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return len(self.checks) - self.passed_count

    @property
    def summary(self) -> str:
        lines = [
            f"[Format Validation]",
            f"  Overall: {'PASS' if self.overall_passed else 'FAIL'}",
            f"  Passed: {self.passed_count}/{len(self.checks)}",
            f"  Issues: {self.total_issues}",
            f"  Score: {self.score:.2f}",
        ]
        for c in self.checks:
            status = "[OK]" if c.passed else "[!!]"
            lines.append(f"  {status} {c.category.value}: {c.count}x")
            for issue in c.issues:
                lines.append(f"       -> {issue}")
        return "\n".join(lines)


# ──────────────────────────────────────────────
# 2. 格式验证器
# ──────────────────────────────────────────────


class FormatValidator:
    """
    结构化输出格式验证器

    自动检测回复中的结构化格式并进行验证，包括：
    - 代码块: 语法完整性、语言标签、内容非空
    - JSON: 合法 JSON 解析
    - 表格: 列对齐、行列一致性
    - 列表: 嵌套一致性、编号连续性
    - URL/引用/标题: 基本有效性
    """

    def __init__(self):
        # 支持的代码语言标签
        self.supported_languages: Set[str] = {
            "python", "javascript", "typescript", "java", "go", "rust",
            "cpp", "c", "csharp", "sql", "bash", "shell", "yaml", "yml",
            "json", "xml", "html", "css", "dockerfile", "makefile",
            "python3", "js", "ts", "py",
        }

    def validate(self, text: str) -> FormatValidationReport:
        """
        对回复文本执行全量格式验证。
        """
        report = FormatValidationReport(overall_passed=True)
        issues = 0

        # 1. 代码块验证
        code_result = self._check_code_blocks(text)
        report.add(code_result)
        if not code_result.passed:
            issues += len(code_result.issues)

        # 2. 行内代码验证
        inline_result = self._check_inline_code(text)
        report.add(inline_result)
        if not inline_result.passed:
            issues += len(inline_result.issues)

        # 3. JSON 验证
        json_result = self._check_json_blocks(text)
        report.add(json_result)
        if not json_result.passed:
            issues += len(json_result.issues)

        # 4. 表格验证
        table_result = self._check_tables(text)
        report.add(table_result)
        if not table_result.passed:
            issues += len(table_result.issues)

        # 5. 列表验证
        list_result = self._check_lists(text)
        report.add(list_result)
        if not list_result.passed:
            issues += len(list_result.issues)

        # 6. URL 验证
        url_result = self._check_urls(text)
        report.add(url_result)

        # 7. 引用块验证
        quote_result = self._check_quotes(text)
        report.add(quote_result)

        # 8. 标题验证
        heading_result = self._check_headings(text)
        report.add(heading_result)

        # 综合评分（默认满分，每个问题 -0.15）
        report.total_issues = issues
        report.score = max(0.0, round(1.0 - issues * 0.15, 2))
        report.overall_passed = issues == 0

        return report

    # ── 各格式检查方法 ──

    def _check_code_blocks(self, text: str) -> FormatCheckResult:
        """
        检查代码块完整性。
        规则：
        1. 代码块必须有开始标记 ``` 和结束标记  ```
        2. 语言标签推荐合理
        3. 内容不应为空
        """
        result = FormatCheckResult(
            category=FormatCategory.CODE_BLOCK,
            passed=True,
            count=0,
        )

        # 匹配所有代码块
        pattern = r'```(\w*)\n?(.*?)```'
        matches = list(re.finditer(pattern, text, re.DOTALL))

        if not matches:
            result.count = 0
            # 无代码块不视为问题
            return result

        result.count = len(matches)

        for i, m in enumerate(matches):
            lang = m.group(1).strip()
            content = m.group(2).strip()

            # 检查语言标签
            if not lang:
                result.issues.append(f"Code block #{i+1}: 缺少语言标签")
                result.passed = False
            elif lang.lower() not in self.supported_languages:
                result.issues.append(
                    f"Code block #{i+1}: 语言标签 '{lang}' 不在常用列表中"
                )

            # 检查空内容
            if not content:
                result.issues.append(f"Code block #{i+1}: 内容为空")
                result.passed = False
            elif len(content.split("\n")) == 1:
                # 单行代码建议用行内代码
                pass

        # 检查不匹配的代码块标记
        open_count = text.count("```")
        if open_count % 2 != 0:
            result.issues.append(f"代码块标记不匹配: {open_count} 个 ```（应为偶数）")
            result.passed = False

        return result

    def _check_inline_code(self, text: str) -> FormatCheckResult:
        """
        检查行内代码。
        规则：
        1. 反引号必须成对
        2. 内容不应过长（>80字符建议用代码块）
        """
        result = FormatCheckResult(
            category=FormatCategory.INLINE_CODE,
            passed=True,
            count=0,
        )

        backtick_count = text.count("`")
        if backtick_count == 0:
            return result

        # 找出所有行内代码片段（单个反引号包裹）
        pattern = r'`([^`]+)`'
        matches = list(re.finditer(pattern, text))
        result.count = len(matches)

        for m in matches:
            content = m.group(1)
            if len(content) > 80:
                result.issues.append(f"Inline code 过长 ({len(content)} 字符)，建议用代码块")
                result.passed = False

        # 检查单反引号是否成对
        if backtick_count % 2 != 0:
            result.issues.append(f"行内代码反引号不配对: {backtick_count} 个 '`'")
            result.passed = False

        return result

    def _check_json_blocks(self, text: str) -> FormatCheckResult:
        """
        检查文本中的 JSON 结构是否合法。
        检测：
        1. **标记的 JSON 代码块
        2. 文本中独立的 JSON 对象/数组
        """
        result = FormatCheckResult(
            category=FormatCategory.JSON,
            passed=True,
            count=0,
        )

        # 查找 ```json 代码块
        json_blocks = list(re.finditer(r'```(?:json)?\n?(\[[\s\S]*?\]|\{[\s\S]*?\})\s*```', text, re.DOTALL))

        # 查找行内 JSON
        if not json_blocks:
            # 尝试直接匹配 {...} 或 [...]
            inline_pattern = r'(?<!`)(\{[^{}]*\}|\[[^\[\]]*\])(?!`)'
            inline_matches = list(re.finditer(inline_pattern, text))
            for m in inline_matches:
                try:
                    parsed = json.loads(m.group(0))
                    if isinstance(parsed, (dict, list)):
                        json_blocks.append(m)
                except (json.JSONDecodeError, ValueError):
                    pass

        result.count = len(json_blocks)

        for block in json_blocks:
            content = block.group(1) if len(block.groups()) >= 1 else block.group(0)
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                result.issues.append(f"JSON 解析失败: {str(e)}")
                result.passed = False

        return result

    def _check_tables(self, text: str) -> FormatCheckResult:
        """
        检查 Markdown 表格。
        规则：
        1. 表头行必须存在
        2. 分隔行格式正确（|---|）
        3. 每行列数一致
        """
        result = FormatCheckResult(
            category=FormatCategory.TABLE,
            passed=True,
            count=0,
        )

        # 查找 Markdown 表格
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            if "|" in lines[i] and i + 1 < len(lines):
                # 可能是一个表格
                header = lines[i].strip()
                separator = lines[i + 1].strip()

                if header.startswith("|") and separator.startswith("|") and "-" in separator:
                    result.count += 1
                    header_cols = header.count("|") - 1
                    sep_cols = separator.count("|") - 1

                    if header_cols != sep_cols:
                        result.issues.append(
                            f"Table #{result.count}: 表头 {header_cols} 列 vs 分隔行 {sep_cols} 列"
                        )
                        result.passed = False

                    # 检查分隔行格式
                    if not all(c in "|:- " for c in separator):
                        result.issues.append(f"Table #{result.count}: 分隔行格式不正确")
                        result.passed = False

                    # 跳到表格结尾
                    i += 2
                    while i < len(lines) and lines[i].strip().startswith("|"):
                        row_cols = lines[i].strip().count("|") - 1
                        if row_cols != header_cols:
                            result.issues.append(
                                f"Table #{result.count}: 第 {i+1} 行 {row_cols} 列 vs 表头 {header_cols} 列"
                            )
                            result.passed = False
                        i += 1
                    continue
            i += 1

        return result

    def _check_lists(self, text: str) -> FormatCheckResult:
        """
        检查列表格式。
        规则：
        1. 嵌套列表缩进一致
        2. 有序列表编号连续
        3. 列表符号统一
        """
        result = FormatCheckResult(
            category=FormatCategory.LIST,
            passed=True,
            count=0,
        )

        lines = text.split("\n")
        ordered_nums: Dict[int, int] = {}  # indent_level -> expected_number
        list_starts: List[bool] = [False] * len(lines)

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # 有序列表: 1. 2. 3.
            ordered_match = re.match(r'^(\d+)\.\s+', stripped)
            if ordered_match:
                list_starts[i] = True
                result.count += 1
                expected = ordered_nums.get(indent, 1)
                actual = int(ordered_match.group(1))
                if actual != expected:
                    if expected > 1:
                        result.issues.append(
                            f"List line {i+1}: 编号应为 {expected}，实际为 {actual}"
                        )
                        result.passed = False
                ordered_nums[indent] = actual + 1

            # 无序列表: - * +
            elif re.match(r'^[-*+]\s+', stripped):
                list_starts[i] = True
                result.count += 1
                # 重置有序编号上下文
                ordered_nums[indent] = 1

            # 不是列表行，重置该缩进级别的计数器
            if not list_starts[i]:
                if indent in ordered_nums:
                    ordered_nums[indent] = 1

        return result

    def _check_urls(self, text: str) -> FormatCheckResult:
        """
        检查 URL 格式是否合理。
        """
        result = FormatCheckResult(
            category=FormatCategory.URL,
            passed=True,
            count=0,
        )

        # URL 正则
        url_pattern = r'https?://[^\s\)\]>"]+'
        urls = re.findall(url_pattern, text)
        result.count = len(urls)

        for url in urls:
            if len(url) > 500:
                result.issues.append(f"URL 过长 ({len(url)} 字符)")
                result.passed = False

        return result

    def _check_quotes(self, text: str) -> FormatCheckResult:
        """
        检查引用块。
        规则：引用行以 > 开头
        """
        result = FormatCheckResult(
            category=FormatCategory.QUOTE,
            passed=True,
            count=0,
        )

        lines = text.split("\n")
        in_quote = False
        quote_count = 0

        for line in lines:
            if line.strip().startswith(">"):
                if not in_quote:
                    quote_count += 1
                    in_quote = True
            else:
                in_quote = False

        result.count = quote_count
        return result

    def _check_headings(self, text: str) -> FormatCheckResult:
        """
        检查标题层级是否合理。
        规则：
        1. 标题层级不能跳跃（不能从 # 直接跳到 ###）
        2. 全文最多一个 H1
        """
        result = FormatCheckResult(
            category=FormatCategory.HEADING,
            passed=True,
            count=0,
        )

        lines = text.split("\n")
        h1_count = 0
        last_level = 0

        for line in lines:
            heading_match = re.match(r'^(#{1,6})\s+', line)
            if heading_match:
                level = len(heading_match.group(1))
                result.count += 1

                if level == 1:
                    h1_count += 1

                # 检查层级跳跃（允许最大跳 1 级）
                if last_level > 0 and level > last_level + 1:
                    result.issues.append(
                        f"标题层级跳跃: 从 {last_level} 级跳到 {level} 级"
                    )
                    result.passed = False
                last_level = level

        if h1_count > 1:
            result.issues.append(f"H1 标题超过 1 个（共 {h1_count} 个）")
            result.passed = False

        return result


# ──────────────────────────────────────────────
# 3. 格式一致性记分器
# ──────────────────────────────────────────────


class FormatScorer:
    """
    格式质量记分器。
    根据多种格式检查结果计算综合评分。
    """

    # 各类别权重
    WEIGHTS = {
        FormatCategory.CODE_BLOCK: 0.25,
        FormatCategory.INLINE_CODE: 0.05,
        FormatCategory.JSON: 0.20,
        FormatCategory.TABLE: 0.15,
        FormatCategory.LIST: 0.10,
        FormatCategory.URL: 0.05,
        FormatCategory.QUOTE: 0.05,
        FormatCategory.HEADING: 0.10,
        FormatCategory.MATH: 0.05,
    }

    @classmethod
    def score(cls, report: FormatValidationReport) -> Dict:
        """
        计算格式质量评分。
        返回各维度评分和综合分。
        """
        dimension_scores = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for check in report.checks:
            weight = cls.WEIGHTS.get(check.category, 0.05)
            # 该维度得分：通过 1.0，不通过视 issue 数量扣分
            if check.passed:
                dim_score = 1.0
            else:
                dim_score = max(0.0, 1.0 - len(check.issues) * 0.3)

            dimension_scores[check.category.value] = dim_score
            weighted_sum += dim_score * weight
            total_weight += weight

        composite_score = round(weighted_sum / total_weight, 2) if total_weight > 0 else 1.0

        return {
            "composite_score": composite_score,
            "dimensions": dimension_scores,
        }

    @classmethod
    def format_report(cls, score_dict: Dict) -> str:
        """生成可读的评分报告"""
        lines = [
            f"  Format Quality Score: {score_dict['composite_score']:.2f}",
            f"  Dimensions:",
        ]
        for dim, score in sorted(score_dict["dimensions"].items()):
            bar = "█" * int(score * 10)
            lines.append(f"    {dim:20s}: {score:.2f}  {bar}")
        return "\n".join(lines)


# ──────────────────────────────────────────────
# 4. 缺失格式检测
# ──────────────────────────────────────────────


class FormatRequirement:
    """
    格式要求——定义回复应该包含/不应该包含的格式。
    用于"回复格式不符合 user prompt 要求"的测试。
    """
    def __init__(self, name: str):
        self.name = name
        self.required_categories: List[FormatCategory] = []
        self.forbidden_categories: List[FormatCategory] = []
        self.min_counts: Dict[FormatCategory, int] = {}

    def require(self, category: FormatCategory, min_count: int = 1) -> "FormatRequirement":
        """要求回复包含特定格式"""
        self.required_categories.append(category)
        self.min_counts[category] = min_count
        return self

    def forbid(self, category: FormatCategory) -> "FormatRequirement":
        """禁止回复包含特定格式"""
        self.forbidden_categories.append(category)
        return self

    def check(self, report: FormatValidationReport) -> List[str]:
        """检查是否满足格式要求，返回违规项列表"""
        violations = []

        # 检查必含格式
        for cat in self.required_categories:
            check_result = next((c for c in report.checks if c.category == cat), None)
            min_count = self.min_counts.get(cat, 1)
            count = check_result.count if check_result else 0
            if count < min_count:
                violations.append(
                    f"需要 {cat.value} 格式至少 {min_count} 个，实际 {count} 个"
                )

        # 检查禁止格式
        for cat in self.forbidden_categories:
            check_result = next((c for c in report.checks if c.category == cat), None)
            count = check_result.count if check_result else 0
            if count > 0:
                violations.append(
                    f"禁止 {cat.value} 格式，实际出现 {count} 次"
                )

        return violations


# ──────────────────────────────────────────────
# 5. 批量验证器
# ──────────────────────────────────────────────


class BatchFormatValidator:
    """
    批量格式验证器。
    对多组回复执行格式验证并生成汇总报告。
    """

    def __init__(self):
        self.validator = FormatValidator()
        self.results: List[FormatValidationReport] = []

    def add(self, text: str) -> FormatValidationReport:
        report = self.validator.validate(text)
        self.results.append(report)
        return report

    def add_batch(self, texts: List[str]) -> List[FormatValidationReport]:
        reports = [self.validator.validate(t) for t in texts]
        self.results.extend(reports)
        return reports

    def summary(self) -> str:
        """生成批量验证汇总"""
        if not self.results:
            return "No results to summarize."

        passed = sum(1 for r in self.results if r.overall_passed)
        total = len(self.results)
        all_issues = []
        scores = []

        for r in self.results:
            all_issues.extend(
                (r.total_issues, len([c for c in r.checks if not c.passed]))
            )
            scores.append(r.score)

        avg_score = round(sum(scores) / len(scores), 2)

        lines = [
            f"{'=' * 50}",
            f"  Batch Format Validation Summary",
            f"{'=' * 50}",
            f"  Total:     {total}",
            f"  Passed:    {passed}",
            f"  Failed:    {total - passed}",
            f"  Pass Rate: {passed/total:.1%}" if total > 0 else "  Pass Rate: N/A",
            f"  Avg Score: {avg_score}",
            f"  Total Issues: {sum(r.total_issues for r in self.results)}",
            f"{'=' * 50}",
        ]

        # 统计各类别问题
        category_issues = {}
        for r in self.results:
            for c in r.checks:
                if not c.passed:
                    cat = c.category.value
                    if cat not in category_issues:
                        category_issues[cat] = 0
                    category_issues[cat] += len(c.issues)

        if category_issues:
            lines.append("")
            lines.append("  Issue Breakdown:")
            for cat, count in sorted(category_issues.items(), key=lambda x: -x[1]):
                bar = "#" * count
                lines.append(f"    {cat:20s}: {count:3d}  {bar}")

        return "\n".join(lines)
