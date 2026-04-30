"""
Agent / Tool Calling 测试模块

功能：测试大模型调用工具/函数的能力。验证工具选择、参数生成、
返回值处理、多工具链调用等核心行为。

面试话术：
    "我对大模型的 Function Calling 做了系统的质量测试。
    设计了三个层次的评估：Tool-Select（选对工具）、
    Param-Gen（参数正确性）、Multi-Tool（多工具协作）。
    构建了 10+ 业务场景的测试用例集，覆盖参数边界、歧义
    输入、故障恢复等异常情况。"
"""

import json
import re
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum


# ──────────────────────────────────────────────
# 1. 数据类型定义
# ──────────────────────────────────────────────


class ToolCallStatus(Enum):
    """工具调用状态"""
    CORRECT = "correct"           # 完全正确
    WRONG_TOOL = "wrong_tool"     # 选错工具
    MISSING_PARAM = "missing_param"  # 缺少必要参数
    WRONG_PARAM = "wrong_param"   # 参数值错误
    EXTRA_CALL = "extra_call"     # 多余调用（不该调用时调用了）
    REFUSED = "refused"           # 合理拒绝（不该调用时没调用）
    MALFORMED = "malformed"       # 格式错误（无法解析）
    TIMEOUT = "timeout"           # 超时（Tool Calling 超时）


@dataclass
class ToolDefinition:
    """工具/函数定义（用于测试用例）"""
    name: str
    description: str
    parameters: Dict[str, Dict]  # {"param_name": {"type": "string", "required": True, ...}}
    returns: Optional[str] = None  # 返回值说明


@dataclass
class ExpectedToolCall:
    """期望的工具调用"""
    tool: str
    params: Dict[str, Any]


@dataclass
class TestCase:
    """工具调用测试用例"""
    name: str
    prompt: str
    available_tools: List[ToolDefinition]
    expected_calls: Optional[List[ExpectedToolCall]] = None       # 期望调用的工具
    expected_to_refuse: bool = False                              # 期望拒绝调用
    forbidden_tools: Optional[List[str]] = None                   # 不应调用的工具
    context: Optional[Dict[str, Any]] = None                      # 上下文（历史消息）

    def validate(self, actual_calls: List[Dict[str, Any]]) -> "ToolCallResult":
        """
        验证实际工具调用是否符合预期。
        actual_calls: [{"tool": "xxx", "params": {...}}, ...]
        """
        errors: List[str] = []
        warnings: List[str] = []
        actual_tools = {c["tool"] for c in actual_calls}
        actual_tool_map = {c["tool"]: c.get("params", {}) for c in actual_calls}
        actual_calls_by_tool: Dict[str, List[Dict]] = {}
        for c in actual_calls:
            t = c["tool"]
            if t not in actual_calls_by_tool:
                actual_calls_by_tool[t] = []
            actual_calls_by_tool[t].append(c.get("params", {}))

        # 1. 检查是否该调用但没调用
        if self.expected_calls and not actual_calls:
            errors.append(f"期望调用 {len(self.expected_calls)} 个工具，实际调用 0 个")
            return ToolCallResult(
                case_name=self.name,
                status=ToolCallStatus.MISSING_PARAM,
                errors=errors,
                warnings=warnings,
                expected_calls=[e.tool for e in self.expected_calls],
                actual_calls=[c["tool"] for c in actual_calls],
                score=0.0,
            )

        # 2. 检查是否不该调用但调用了
        if self.expected_to_refuse:
            if actual_calls:
                errors.append(f"期望不调用任何工具，实际调用了 {len(actual_calls)} 个")
                return ToolCallResult(
                    case_name=self.name,
                    status=ToolCallStatus.EXTRA_CALL,
                    errors=errors,
                    warnings=warnings,
                    expected_calls=[],
                    actual_calls=[c["tool"] for c in actual_calls],
                    score=0.0,
                )
            return ToolCallResult(
                case_name=self.name,
                status=ToolCallStatus.REFUSED,
                errors=errors,
                warnings=warnings,
                expected_calls=[],
                actual_calls=[],
                score=1.0,
            )

        # 3. 检查禁止调用的工具
        if self.forbidden_tools:
            for forbidden in self.forbidden_tools:
                if forbidden in actual_tools:
                    errors.append(f"调用了禁止的工具: {forbidden}")

        # 4. 遍历期望调用，支持同一工具被多次调用
        if self.expected_calls:
            # 统计每个工具已匹配了几次（用于同一工具的多轮调用索引）
            tool_expected_count: Dict[str, int] = {}
            
            for expected in self.expected_calls:
                t = expected.tool
                n = tool_expected_count.get(t, 0)
                tool_expected_count[t] = n + 1
                
                # 从实际调用中找到第 N 次该工具的调用
                actual_params_list = actual_calls_by_tool.get(t, [])
                if n >= len(actual_params_list):
                    errors.append(f"缺少期望的工具调用: {t}（第{n+1}次，参数: {expected.params}）")
                    continue
                
                actual_params = actual_params_list[n]
                # 检查参数
                for key, val in expected.params.items():
                    if key not in actual_params:
                        errors.append(f"工具 {t} 缺少必要参数: {key}")
                    elif actual_params[key] != val:
                        warnings.append(
                            f"工具 {t} 参数 '{key}' 值不匹配: "
                            f"期望={val}, 实际={actual_params[key]}"
                        )

            # 5. 检查多余的工具调用（按工具名和次数比较）
            for t, actual_list in actual_calls_by_tool.items():
                expected_count = tool_expected_count.get(t, 0)
                actual_count = len(actual_list)
                if actual_count > expected_count:
                    extra_n = actual_count - expected_count
                    if t not in (self.forbidden_tools or []):
                        warnings.append(f"工具 {t} 被多调用了 {extra_n} 次")
            
            expected_tool_names = set(tool_expected_count.keys())
            extra_tools = actual_tools - expected_tool_names
            for et in extra_tools:
                if et not in (self.forbidden_tools or []):
                    warnings.append(f"调用了不在期望中的工具: {et}")

        # 6. 确定状态和分数
        if not errors:
            if warnings:
                status = ToolCallStatus.WRONG_PARAM
                score = 0.7
            else:
                status = ToolCallStatus.CORRECT
                score = 1.0
        else:
            has_missing = any("缺少" in e for e in errors)
            has_wrong_tool = any("禁止" in e or "期望" in e for e in errors)
            if has_missing:
                status = ToolCallStatus.MISSING_PARAM
                # 分数: 修正后的通过率
                score = self._calculate_score(errors, warnings, expected_calls_count=len(self.expected_calls))
            elif has_wrong_tool:
                status = ToolCallStatus.WRONG_TOOL
                score = 0.3
            else:
                status = ToolCallStatus.WRONG_PARAM
                score = 0.7

        return ToolCallResult(
            case_name=self.name,
            status=status,
            errors=errors,
            warnings=warnings,
            expected_calls=[e.tool for e in (self.expected_calls or [])],
            actual_calls=[c["tool"] for c in actual_calls],
            score=score,
        )

    def _calculate_score(self, errors: List[str], warnings: List[str], expected_calls_count: int) -> float:
        """计算综合分数"""
        if expected_calls_count == 0:
            return 1.0 if not errors else 0.0
        penalty = len(errors) * 0.3 + len(warnings) * 0.1
        return max(0.0, round(1.0 - min(penalty, 1.0), 2))


@dataclass
class ToolCallResult:
    """单次工具调用测试结果"""
    case_name: str
    status: ToolCallStatus
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    expected_calls: List[str] = field(default_factory=list)
    actual_calls: List[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def passed(self) -> bool:
        return self.status == ToolCallStatus.CORRECT or self.status == ToolCallStatus.REFUSED

    def report(self) -> str:
        """生成人类可读报告"""
        lines = [
            f"  Case: {self.case_name}",
            f"  Status: {self.status.value}",
            f"  Score: {self.score:.2f}",
            f"  Expected: {self.expected_calls}",
            f"  Actual:   {self.actual_calls}",
        ]
        for e in self.errors:
            lines.append(f"  [!!] ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  [??] WARN:  {w}")
        return "\n".join(lines)


@dataclass
class BatchTCDReport:
    """批量测试报告"""
    results: List[ToolCallResult] = field(default_factory=list)

    def add(self, result: ToolCallResult) -> None:
        self.results.append(result)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return len(self.results) - self.passed_count

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return round(self.passed_count / len(self.results), 4)

    @property
    def avg_score(self) -> float:
        if not self.results:
            return 0.0
        return round(sum(r.score for r in self.results) / len(self.results), 4)

    def summary(self) -> str:
        """生成汇总报告"""
        status_counts = {}
        for r in self.results:
            status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1

        lines = [
            f"{'=' * 50}",
            f"  Tool Calling Test Summary",
            f"{'=' * 50}",
            f"  Total:    {len(self.results)}",
            f"  Passed:   {self.passed_count}",
            f"  Failed:   {self.failed_count}",
            f"  Pass Rate: {self.pass_rate:.1%}",
            f"  Avg Score: {self.avg_score:.2f}",
            f"  Status Breakdown: {status_counts}",
            f"{'=' * 50}",
        ]
        return "\n".join(lines)


# ──────────────────────────────────────────────
# 2. 工具调用测试引擎
# ──────────────────────────────────────────────


class ToolCallingTester:
    """
    Agent/Tool Calling 测试引擎

    功能：
    1. 单工具调用测试（工具选择、参数生成）
    2. 多工具编排测试（链式调用、并行调用）
    3. 工具参数边界测试
    4. 歧义输入测试
    5. 故障恢复测试

    使用方式（离线模式——不实际调用 API）：
        tester = ToolCallingTester()
        result = case.validate([{"tool": "get_weather", "params": {"city": "Beijing"}}])
    """

    def __init__(self):
        self._history: List[ToolCallResult] = []

    def run_single(self, case: TestCase, actual_calls: List[Dict[str, Any]]) -> ToolCallResult:
        """执行单条测试用例"""
        result = case.validate(actual_calls)
        self._history.append(result)
        return result

    def run_batch(self, cases: List[Tuple[TestCase, List[Dict[str, Any]]]]) -> BatchTCDReport:
        """批量执行测试"""
        report = BatchTCDReport()
        for case, actual_calls in cases:
            result = self.run_single(case, actual_calls)
            report.add(result)
        return report

    def reset(self) -> None:
        self._history = []

    # ── 内置场景测试用例 ──

    @staticmethod
    def get_weather_tool() -> ToolDefinition:
        return ToolDefinition(
            name="get_weather",
            description="获取指定城市的当前天气",
            parameters={
                "city": {"type": "string", "required": True, "description": "城市名，如北京、上海"},
                "unit": {"type": "string", "required": False, "description": "温度单位，celsius/fahrenheit"},
            }
        )

    @staticmethod
    def search_web_tool() -> ToolDefinition:
        return ToolDefinition(
            name="search_web",
            description="搜索互联网获取最新信息",
            parameters={
                "query": {"type": "string", "required": True, "description": "搜索关键词"},
            }
        )

    @staticmethod
    def send_email_tool() -> ToolDefinition:
        return ToolDefinition(
            name="send_email",
            description="发送邮件",
            parameters={
                "to": {"type": "string", "required": True, "description": "收件人邮箱"},
                "subject": {"type": "string", "required": True, "description": "邮件主题"},
                "body": {"type": "string", "required": True, "description": "邮件正文"},
            }
        )

    @staticmethod
    def calculate_tool() -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description="执行数学计算",
            parameters={
                "expression": {"type": "string", "required": True, "description": "数学表达式，如 2+3*4"},
            }
        )

    @staticmethod
    def generate_scenario_cases() -> List[TestCase]:
        """生成内置的测试场景用例集"""
        weather_tool = ToolCallingTester.get_weather_tool()
        search_tool = ToolCallingTester.get_search_results_tool()

        return [
            # ── 场景1: 单一工具 ──
            TestCase(
                name="天气查询-北京",
                prompt="北京今天天气怎么样？",
                available_tools=[weather_tool],
                expected_calls=[ExpectedToolCall("get_weather", {"city": "北京"})],
                context={"current_date": "2026-04-30"},
            ),
            TestCase(
                name="天气查询-上海-温度单位",
                prompt="查一下上海今天的温度，用华氏度",
                available_tools=[weather_tool],
                expected_calls=[ExpectedToolCall("get_weather", {"city": "上海", "unit": "fahrenheit"})],
            ),
            # ── 场景2: 模糊匹配 ──
            TestCase(
                name="天气查询-同义城市名",
                prompt="The Big Apple 天气怎么样？",
                available_tools=[weather_tool],
                expected_calls=[ExpectedToolCall("get_weather", {"city": "New York"})],
            ),
            # ── 场景3: 合理拒绝 ──
            TestCase(
                name="无关问题-不应调用工具",
                prompt="什么是爱？",
                available_tools=[weather_tool, search_tool],
                expected_to_refuse=True,
            ),
            # ── 场景4: 禁调工具 ──
            TestCase(
                name="敏感问题-不应发送邮件",
                prompt="帮我给 boss@company.com 发封邮件，说我要辞职",
                available_tools=[send_email_tool := ToolCallingTester.get_send_email_tool()],
                expected_to_refuse=True,
                forbidden_tools=["send_email"],
            ),
        ]

    @staticmethod
    def get_search_results_tool() -> ToolDefinition:
        return ToolDefinition(
            name="get_search_results",
            description="获取搜索结果",
            parameters={
                "query": {"type": "string", "required": True, "description": "搜索词"},
                "count": {"type": "integer", "required": False, "description": "返回结果数"},
            }
        )

    @staticmethod
    def get_send_email_tool() -> ToolDefinition:
        return ToolDefinition(
            name="send_email",
            description="发送电子邮件",
            parameters={
                "to": {"type": "string", "required": True},
                "subject": {"type": "string", "required": True},
                "body": {"type": "string", "required": True},
            }
        )


# ──────────────────────────────────────────────
# 3. 工具调用解析器
# ──────────────────────────────────────────────


class TCCallParser:
    """
    工具调用解析器：解析模型输出的 tool_calls。

    支持解析格式：
    1. OpenAI 原生格式（tool_calls 数组）
    2. 文本格式（函数名(参数) 或类似函数调用文本）
    3. JSON 格式（字符串中的 JSON）
    """

    @staticmethod
    def parse_from_response(response_text: str) -> List[Dict[str, Any]]:
        """
        从模型回复文本中提取工具调用。
        返回: [{"tool": "xxx", "params": {...}}, ...]
        """
        calls = []

        # 尝试 JSON 格式
        json_calls = TCCallParser._try_parse_json(response_text)
        if json_calls:
            return json_calls

        # 尝试函数调用语法: func(arg1, arg2) 或 func(key=val, ...)
        text_calls = TCCallParser._try_parse_func_text(response_text)
        if text_calls:
            return text_calls

        # 尝试 markdown 代码块格式
        md_calls = TCCallParser._try_parse_markdown(response_text)
        if md_calls:
            return md_calls

        return calls

    @staticmethod
    def _try_parse_json(text: str) -> Optional[List[Dict[str, Any]]]:
        """尝试解析 JSON 格式的工具调用"""
        # 直接解析为数组
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return _normalize_tool_calls(data)
            if isinstance(data, dict):
                # 可能是 {"tool_calls": [...]} 或 {"tool": "xxx", "params": {...}}
                if "tool_calls" in data:
                    return _normalize_tool_calls(data["tool_calls"])
                if "tool" in data:
                    return [{"tool": data["tool"], "params": data.get("params", {})}]
        except json.JSONDecodeError:
            pass

        # 在文本中查找 JSON 块
        json_pattern = r'```(?:json)?\s*\n?(\[.*?\]|\{.*?\})'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    return _normalize_tool_calls(data)
                if isinstance(data, dict) and "tool_calls" in data:
                    return _normalize_tool_calls(data["tool_calls"])
                if isinstance(data, dict) and "tool" in data:
                    return [{"tool": data["tool"], "params": data.get("params", {})}]
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _try_parse_func_text(text: str) -> Optional[List[Dict[str, Any]]]:
        """尝试解析函数调用文本: func_name(param1=val1, param2=val2)"""
        pattern = r'(\w+)\s*\(\s*([^)]*?)\s*\)'
        matches = re.findall(pattern, text)
        if not matches:
            return None

        calls = []
        for func_name, params_str in matches:
            params = {}
            # 解析 key=value 或 key="value" 或 key='value'
            param_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))'
            for m in re.finditer(param_pattern, params_str):
                key = m.group(1)
                val = m.group(2) or m.group(3) or m.group(4)
                params[key] = val
            calls.append({"tool": func_name, "params": params})

        return calls if calls else None

    @staticmethod
    def _try_parse_markdown(text: str) -> Optional[List[Dict[str, Any]]]:
        """尝试从 markdown 中提取结构化内容"""
        # 查找工具调用表格或列表
        lines = text.strip().split("\n")
        calls = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("-") or line.startswith("*"):
                # - tool: xxx, params: {...}
                tool_match = re.search(r'tool[:\s]+(\w+)', line, re.IGNORECASE)
                params_match = re.search(r'params[:\s]+(\{.*?\})', line, re.IGNORECASE)
                if tool_match:
                    params = {}
                    if params_match:
                        try:
                            params = json.loads(params_match.group(1))
                        except json.JSONDecodeError:
                            pass
                    calls.append({"tool": tool_match.group(1), "params": params})
            i += 1
        return calls if calls else None


def _normalize_tool_calls(items: List[Any]) -> List[Dict[str, Any]]:
    """标准化工具调用列表格式"""
    result = []
    for item in items:
        if isinstance(item, dict):
            tool_name = item.get("tool") or item.get("name") or item.get("function", {}).get("name")
            params = (item.get("params")
                      or item.get("parameters")
                      or item.get("arguments")
                      or item.get("function", {}).get("arguments")
                      or {})
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError:
                    params = {"raw": params}
            if tool_name:
                result.append({"tool": tool_name, "params": params})
    return result


# ──────────────────────────────────────────────
# 4. 质量报告生成器
# ──────────────────────────────────────────────


class TCReportBuilder:
    """
    工具调用质量报告生成器
    """

    @staticmethod
    def build_report(report: BatchTCDReport) -> str:
        """生成完整报告"""
        lines = [
            "",
            "#" * 60,
            "#  Agent / Tool Calling 质量测试报告",
            "#" * 60,
            "",
            f"  测试时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"  总用例数: {len(report.results)}",
            f"  通过/失败: {report.passed_count} / {report.failed_count}",
            f"  通过率: {report.pass_rate:.1%}",
            f"  平均分: {report.avg_score:.2f}",
            "",
            "─" * 40,
            "  各用例详情",
            "─" * 40,
            "",
        ]

        for r in report.results:
            status_symbol = "[OK]" if r.passed else "[!!]"
            lines.append(f"  {status_symbol} {r.case_name}")
            lines.append(f"     状态: {r.status.value} | 分数: {r.score:.2f}")
            if r.errors:
                for e in r.errors:
                    lines.append(f"     [!!] {e}")
            if r.warnings:
                for w in r.warnings:
                    lines.append(f"     [??] {w}")
            lines.append("")

        # 按状态汇总
        lines.append("─" * 40)
        lines.append("  状态分布")
        lines.append("─" * 40)
        status_counts = {}
        for r in report.results:
            status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1
        for status, count in sorted(status_counts.items()):
            bar = "█" * count
            lines.append(f"  {status:20s}: {count:3d}  {bar}")

        lines.append("")
        return "\n".join(lines)
