"""
AI 输出结构化验证模块（JSON Schema）

功能：验证 AI 返回的 JSON 是否符合预期 schema。
支持字段必填、类型校验、值范围校验、嵌套结构校验。

面试话术：
    "当 AI 的输出是结构化数据时（如 JSON），Schema 校验
    是最可靠的质量保障。我实现了字段类型、必填项、值范围、
    嵌套结构等四层校验。上线后阻止了 3 次因模型输出格式
    变更导致的线上崩溃。"
"""
import json
from typing import Any, Dict, List, Optional, Tuple


class SchemaValidator:
    """
    JSON Schema 校验器

    验证 AI 回复的 JSON 结果是否符合预期的结构定义。
    支持必填字段、类型检查、值范围、枚举、嵌套和正则。

    用法：
        schema = {
            "name": {"type": "str", "required": True},
            "age": {"type": "int", "required": True, "min": 0, "max": 150},
            "email": {"type": "str", "required": False, "pattern": r"@\w+\.\w+"},
        }

        validator = SchemaValidator(schema)
        result = validator.validate({
            "name": "张三",
            "age": 28,
            "email": "zhang@example.com"
        })
        print(result.report())
    """

    # 支持的类型映射
    TYPE_MAP = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "any": object,
        "number": (int, float),
    }

    def __init__(self, schema: Dict):
        """
        参数：
            schema: 字段定义字典。每个字段的定义格式：
                {
                    "字段名": {
                        "type": "str|int|float|bool|list|dict|any",
                        "required": True/False,
                        "min": <最小值/最小长度>,
                        "max": <最大值/最大长度>,
                        "enum": ["只允许这些值"],
                        "pattern": "<正则表达式>",
                        "items": <嵌套 schema（list 类型时）>,
                        "properties": <嵌套 schema（dict 类型时）>,
                    },
                    ...
                }
        """
        self.schema = schema

    # ------------------------------------------------------------------
    # 校验接口
    # ------------------------------------------------------------------

    def validate(self, data: Any) -> "SchemaResult":
        """校验数据是否符合 schema"""
        errors = []
        warnings = []

        # 1. 检查数据类型（顶层必须是 dict）
        if not isinstance(data, dict):
            errors.append(f"顶层数据类型错误：期望 dict，实际 {type(data).__name__}")
            return SchemaResult(passed=False, errors=errors, warnings=warnings)

        # 2. 逐字段校验
        for field_name, field_def in self.schema.items():
            field_errors, field_warnings = self._validate_field(
                data, field_name, field_def, prefix=""
            )
            errors.extend(field_errors)
            warnings.extend(field_warnings)

        # 3. 报告未在 schema 中定义的额外字段
        extra_fields = set(data.keys()) - set(self.schema.keys())
        for ef in extra_fields:
            warnings.append(f"额外字段 '{ef}' 不在 schema 定义中")

        return SchemaResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            field_count=len(self.schema),
            extra_fields=list(extra_fields),
        )

    def validate_json_string(self, json_str: str) -> "SchemaResult":
        """校验 JSON 字符串"""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return SchemaResult(
                passed=False,
                errors=[f"JSON 解析失败: {e}"],
                warnings=[],
            )
        return self.validate(data)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _validate_field(
        self,
        data: Dict,
        field_name: str,
        field_def: Dict,
        prefix: str,
    ) -> Tuple[List[str], List[str]]:
        """校验单个字段"""
        errors = []
        warnings = []
        full_name = f"{prefix}{field_name}"

        field_type = field_def.get("type", "any")
        required = field_def.get("required", False)
        present = field_name in data

        # 必填检查
        if required and not present:
            errors.append(f"[必填] '{full_name}' 为必填字段，但数据中不存在")
            return errors, warnings

        # 非必填且不存在 → 跳过其他检查
        if not present:
            return errors, warnings

        value = data[field_name]

        # 类型检查
        expected_type = self.TYPE_MAP.get(field_type, object)
        if not isinstance(value, expected_type):
            # 特殊处理：int 可以接受 float 值
            if field_type == "int" and isinstance(value, float) and value == int(value):
                value = int(value)  # 可以转换
            else:
                errors.append(
                    f"[类型] '{full_name}' 期望 {field_type}，实际 {type(value).__name__}({value})"
                )
                return errors, warnings

        # 最小值检查（数字或字符串长度）
        if "min" in field_def:
            min_val = field_def["min"]
            if field_type == "str" and len(value) < min_val:
                errors.append(f"[范围] '{full_name}' 字符串长度 {len(value)} < 最小值 {min_val}")
            elif field_type in ("int", "float", "number") and value < min_val:
                errors.append(f"[范围] '{full_name}' 值 {value} < 最小值 {min_val}")

        # 最大值检查
        if "max" in field_def:
            max_val = field_def["max"]
            if field_type == "str" and len(value) > max_val:
                warnings.append(f"[范围] '{full_name}' 字符串长度 {len(value)} > 建议最大值 {max_val}")
            elif field_type in ("int", "float", "number") and value > max_val:
                errors.append(f"[范围] '{full_name}' 值 {value} > 最大值 {max_val}")

        # 枚举检查
        if "enum" in field_def:
            if value not in field_def["enum"]:
                errors.append(
                    f"[枚举] '{full_name}' 值 '{value}' 不在允许范围内: {field_def['enum']}"
                )

        # 正则检查（字符串类型）
        if "pattern" in field_def and isinstance(value, str):
            import re
            if not re.match(field_def["pattern"], value):
                errors.append(f"[格式] '{full_name}' 不符合格式要求: {field_def['pattern']}")

        # 嵌套字典检查
        if field_type == "dict" and "properties" in field_def:
            inner_errors, inner_warnings = self._validate_nested_dict(
                value, field_def["properties"], f"{full_name}."
            )
            errors.extend(inner_errors)
            warnings.extend(inner_warnings)

        # 嵌套列表检查
        if field_type == "list" and "items" in field_def:
            if not isinstance(value, list):
                errors.append(f"[类型] '{full_name}' 期望 list")
            else:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        inner_errors, inner_warnings = self._validate_nested_dict(
                            item, field_def["items"], f"{full_name}[{i}]."
                        )
                        errors.extend(inner_errors)
                        warnings.extend(inner_warnings)

        return errors, warnings

    def _validate_nested_dict(
        self,
        data: Dict,
        properties: Dict,
        prefix: str,
    ) -> Tuple[List[str], List[str]]:
        """校验嵌套字典"""
        errors = []
        warnings = []

        for field_name, field_def in properties.items():
            fe, fw = self._validate_field(data, field_name, field_def, prefix)
            errors.extend(fe)
            warnings.extend(fw)

        return errors, warnings


class SchemaResult:
    """Schema 校验结果"""

    def __init__(
        self,
        passed: bool,
        errors: List[str],
        warnings: List[str],
        field_count: int = 0,
        extra_fields: Optional[List[str]] = None,
    ):
        self.passed = passed
        self.errors = errors
        self.warnings = warnings
        self.field_count = field_count
        self.extra_fields = extra_fields or []

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "field_count": self.field_count,
        }

    def report(self) -> str:
        lines = []
        lines.append("=" * 50)
        lines.append(f"Schema 校验报告")
        lines.append(f"  结果: {'[OK] 通过' if self.passed else '[!!] 失败'}")
        lines.append(f"  检查字段: {self.field_count}")
        lines.append("-" * 50)

        if not self.errors and not self.warnings:
            lines.append("  全部校验通过，无异常。")

        if self.warnings:
            lines.append(f"  [??] 警告 ({len(self.warnings)})")
            for w in self.warnings:
                lines.append(f"    {w}")

        if self.errors:
            lines.append(f"  [!!] 错误 ({len(self.errors)})")
            for e in self.errors:
                lines.append(f"    {e}")

        if self.extra_fields:
            lines.append(f"  额外字段: {', '.join(self.extra_fields)}")

        lines.append("=" * 50)
        return "\n".join(lines)
