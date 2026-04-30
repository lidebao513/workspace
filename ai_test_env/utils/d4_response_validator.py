"""响应验证器 - AI API 响应结构验证模块

功能说明：
    验证 API 返回的每个字段，生成结构化的验证报告，支持自动化测试和质量保障。

作者：测试团队
创建日期：2024年
版本：1.0.0

模块结构：
    - ResponseValidator: 静态验证器类
    - 提供 9 个字段的逐一验证（id/object/created/model/choices/usage 等）
    - 支持 PASS/FAIL/WARN 三种状态标记
    - 生成详细的验证报告和汇总统计

面试话术参考：
    "我写了响应验证器，每次调用后自动检查 choices、usage、finish_reason
    等所有字段。测试报告中会标明每个字段的状态——字段缺失标 FAIL，
    字段异常标 WARN，所有正常才标 PASS。这个验证器在我代码上线前
    帮我捉到过 3 次字段变化的问题。"
"""
import time


class ResponseValidator:
    """
    API 响应验证器

    对 AI API 响应进行全面的字段验证，确保响应结构符合预期。

    典型用法：
        report = ResponseValidator.validate(response)
        if report["all_pass"]:
            print("所有字段验证通过")
        else:
            for check in report["checks"]:
                print(f"  [{check['status']}] {check['field']}: {check['message']}")

    验证字段列表：
        - id: 响应唯一标识
        - object: 响应类型（预期为 chat.completion）
        - created: 创建时间戳
        - model: 使用的模型名称
        - choices: 回复选项列表
        - finish_reason: 回复结束原因
        - message.role: 消息角色
        - message.content: 消息内容
        - usage: Token 使用情况
    """

    # 预期的响应类型
    EXPECTED_OBJECT = "chat.completion"
    # 预期的消息角色
    EXPECTED_ROLE = "assistant"
    # 合法的结束原因
    VALID_FINISH_REASONS = {"stop", "length", "content_filter", None}

    @staticmethod
    def validate(response):
        """
        全面验证 API 响应

        对响应对象的 9 个关键字段逐一进行验证，生成结构化报告。

        Args:
            response: API 响应对象

        Returns:
            dict: 验证报告，包含以下结构:
                {
                    "all_pass": bool,           # 是否全部通过
                    "checks": [                 # 各字段检查结果
                        {"field": str, "status": str, "message": str},
                        ...
                    ],
                    "summary": {                # 汇总统计
                        "total": int,           # 总检查数
                        "passed": int,          # 通过数
                        "failed": int,          # 失败数
                        "warned": int           # 警告数
                    }
                }
        """
        # 存储各字段的检查结果
        checks = []

        # 逐一验证各字段
        checks.append(ResponseValidator._check_id(response))
        checks.append(ResponseValidator._check_object(response))
        checks.append(ResponseValidator._check_created(response))
        checks.append(ResponseValidator._check_model(response))
        checks.append(ResponseValidator._check_choices(response))
        checks.append(ResponseValidator._check_finish_reason(response))
        checks.append(ResponseValidator._check_role(response))
        checks.append(ResponseValidator._check_content(response))
        checks.append(ResponseValidator._check_usage(response))

        # 统计各状态数量
        passed = sum(1 for c in checks if c["status"] == "PASS")
        failed = sum(1 for c in checks if c["status"] == "FAIL")
        warned = sum(1 for c in checks if c["status"] == "WARN")

        # 返回完整的验证报告
        return {
            "all_pass": failed == 0,
            "checks": checks,
            "summary": {"total": len(checks), "passed": passed, "failed": failed, "warned": warned},
        }

    @staticmethod
    def _check_id(response):
        """验证响应 ID"""
        if not response.id:
            return {"field": "id", "status": "FAIL", "message": "id 为空"}
        if "chatcmpl" not in response.id.lower():
            return {"field": "id", "status": "WARN", "message": f"id 格式异常: {response.id}"}
        return {"field": "id", "status": "PASS", "message": response.id[:40]}

    @staticmethod
    def _check_object(response):
        """验证响应类型"""
        if response.object != ResponseValidator.EXPECTED_OBJECT:
            return {"field": "object", "status": "FAIL",
                    "message": f"预期='{ResponseValidator.EXPECTED_OBJECT}', 实际='{response.object}'"}
        return {"field": "object", "status": "PASS", "message": response.object}

    @staticmethod
    def _check_created(response):
        """验证创建时间戳"""
        now = int(time.time())
        if not response.created:
            return {"field": "created", "status": "FAIL", "message": "created 为空"}
        # 允许 5 分钟内的时间偏差
        if abs(response.created - now) > 300:
            return {"field": "created", "status": "WARN",
                    "message": f"时间戳偏差: response={response.created}, now={now}"}
        return {"field": "created", "status": "PASS", "message": f"时间戳 {response.created}"}

    @staticmethod
    def _check_model(response):
        """验证模型名称"""
        if not response.model:
            return {"field": "model", "status": "FAIL", "message": "model 为空"}
        return {"field": "model", "status": "PASS", "message": response.model}

    @staticmethod
    def _check_choices(response):
        """验证选项列表"""
        if not response.choices:
            return {"field": "choices", "status": "FAIL", "message": "choices 为空"}
        if len(response.choices) < 1:
            return {"field": "choices", "status": "FAIL", "message": f"choices 长度为 {len(response.choices)}"}
        if len(response.choices) > 1:
            return {"field": "choices", "status": "WARN", "message": f"choices > 1: {len(response.choices)} 个"}
        return {"field": "choices", "status": "PASS", "message": f"{len(response.choices)} 个"}

    @staticmethod
    def _check_finish_reason(response):
        """验证结束原因"""
        if not response.choices:
            return {"field": "finish_reason", "status": "FAIL", "message": "choices 为空"}
        reason = response.choices[0].finish_reason
        if reason not in ResponseValidator.VALID_FINISH_REASONS:
            return {"field": "finish_reason", "status": "WARN", "message": f"未知: {reason}"}
        return {"field": "finish_reason", "status": "PASS", "message": reason}

    @staticmethod
    def _check_role(response):
        """验证消息角色"""
        if not response.choices:
            return {"field": "message.role", "status": "FAIL", "message": "choices 为空"}
        role = response.choices[0].message.role
        if role != ResponseValidator.EXPECTED_ROLE:
            return {"field": "message.role", "status": "FAIL",
                    "message": f"预期='{ResponseValidator.EXPECTED_ROLE}', 实际='{role}'"}
        return {"field": "message.role", "status": "PASS", "message": role}

    @staticmethod
    def _check_content(response):
        """验证消息内容"""
        if not response.choices:
            return {"field": "message.content", "status": "FAIL", "message": "choices 为空"}
        content = response.choices[0].message.content
        if content is None:
            return {"field": "message.content", "status": "FAIL", "message": "content 为 None"}
        if content == "":
            return {"field": "message.content", "status": "WARN", "message": "content 为空"}
        return {"field": "message.content", "status": "PASS", "message": f"长度 {len(content)} 字符"}

    @staticmethod
    def _check_usage(response):
        """验证 Token 使用情况"""
        if not response.usage:
            return {"field": "usage", "status": "FAIL", "message": "usage 为空"}
        usage = response.usage
        
        # 提取各 Token 字段
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        total = getattr(usage, "total_tokens", None)
        
        # 检查字段完整性
        if prompt is None or completion is None or total is None:
            return {"field": "usage", "status": "FAIL", "message": "缺少子字段"}
        
        # 检查数值合理性
        if prompt < 0 or completion < 0 or total < 0:
            return {"field": "usage", "status": "FAIL", "message": "Token 为负数"}
        
        # 验证 Token 计算一致性
        if prompt + completion != total:
            return {"field": "usage", "status": "FAIL",
                    "message": f"P({prompt}) + C({completion}) != T({total})"}
        
        return {"field": "usage", "status": "PASS", 
                "message": f"P={prompt} C={completion} T={total}"}

    @staticmethod
    def print_report(report):
        """打印验证报告

        格式化输出验证结果，便于查看和日志记录。

        Args:
            report: 由 validate 方法返回的验证报告
        """
        print(f"\n{'=' * 50}")
        print(f"API 响应验证报告")
        print(f"{'=' * 50}")
        
        # 输出各字段检查结果
        for check in report["checks"]:
            status = check["status"]
            # 根据状态选择前缀符号
            if status == "PASS":
                prefix = "[OK]"
            elif status == "FAIL":
                prefix = "[!!]"
            else:
                prefix = "[??]"
            print(f"  {prefix} [{status}] {check['field']}: {check['message']}")
        
        # 输出汇总统计
        s = report["summary"]
        print(f"\n  汇总: {s['passed']}/{s['total']} 通过, {s['failed']} 失败, {s['warned']} 警告")
        
        # 输出最终结论
        if report["all_pass"]:
            print(f"  [OK] 全部字段验证通过")
        else:
            print(f"  [!!] 存在需要修复的问题")
