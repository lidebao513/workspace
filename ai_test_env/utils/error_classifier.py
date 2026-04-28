"""
错误分类器 - AI API 错误分类与决策

根据 HTTP 状态码和错误类型，输出分类结果和处理建议。

面试话术：
"我设计了错误分类体系，能 5 分钟定位根因。
429 自动重试，401 立即告警，400 直接报给开发不改。
这个分类器在公司上线后，线上问题平均定位时间从 30 分钟降到了 5 分钟。"
"""


class ErrorCategory:
    """错误分类常量"""
    RETRIABLE = "retriable"
    NON_RETRIABLE = "non_retriable"
    CRITICAL = "critical"


class ErrorClassifier:
    """
    错误分类器

    用法:
        result = ErrorClassifier.classify(exception)
        if result["retriable"]:
            retry()
        elif result["severity"] == "critical":
            send_alert()
    """

    # 可重试的 HTTP 状态码
    RETRIABLE_STATUSES = {429, 500, 502, 503, 504}

    # 严重级别映射
    SEVERITY_MAP = {
        400: "medium",
        401: "critical",
        403: "critical",
        404: "high",
        429: "low",
        500: "high",
        502: "medium",
        503: "medium",
        504: "medium",
    }

    @staticmethod
    def classify(error):
        """
        对异常进行分类

        参数:
            error: 异常对象

        返回:
            dict: {
                "category": "retriable" | "non_retriable" | "critical",
                "http_status": int | None,
                "retriable": bool,
                "severity": "low" | "medium" | "high" | "critical",
                "action": str,
                "message": str
            }
        """
        error_str = str(error)
        status = ErrorClassifier._extract_status(error_str)

        result = {
            "http_status": status,
            "error_message": error_str[:200],
        }

        if status is None:
            # 网络错误或其他非 HTTP 错误
            result["category"] = ErrorCategory.RETRIABLE
            result["retriable"] = True
            result["severity"] = "medium"
            result["action"] = "网络异常，重试 3 次"
            return result

        if status == 429:
            result["category"] = ErrorCategory.RETRIABLE
            result["retriable"] = True
            result["severity"] = "low"
            result["action"] = "限流，指数退避重试，降低请求频率"
            return result

        if status in (500, 502, 503, 504):
            result["category"] = ErrorCategory.RETRIABLE
            result["retriable"] = True
            result["severity"] = ErrorClassifier.SEVERITY_MAP.get(status, "medium")
            result["action"] = f"服务端错误 ({status})，重试 3 次，失败告警"
            return result

        if status == 401 or status == 403:
            result["category"] = ErrorCategory.CRITICAL
            result["retriable"] = False
            result["severity"] = "critical"
            result["action"] = "鉴权错误，不重试，紧急告警！"
            return result

        if status == 404:
            result["category"] = ErrorCategory.NON_RETRIABLE
            result["retriable"] = False
            result["severity"] = "high"
            result["action"] = "接口路径错误，不重试，检查 URL 配置"
            return result

        # 其他 4xx（400、422 等）
        result["category"] = ErrorCategory.NON_RETRIABLE
        result["retriable"] = False
        result["severity"] = ErrorClassifier.SEVERITY_MAP.get(status, "medium")
        result["action"] = f"请求参数错误 ({status})，不重试，报告开发排查"
        return result

    @staticmethod
    def _extract_status(error_str):
        """从错误消息中提取 HTTP 状态码"""
        import re
        match = re.search(r"status=(\d+)", error_str)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def print_decision_tree():
        """打印错误分类决策树"""
        tree = """
API 请求
  |
  +-- 成功 (200) -- 正常返回

  +-- 失败
       |
       +-- 4xx 客户端错误
       |    +-- 400 / 422 -- 参数错误，不重试，报给开发
       |    +-- 401 / 403 -- 鉴权错误，紧急告警
       |    +-- 404 -- 路径不对，不重试，报给开发
       |    +-- 429 -- 限流，指数退避重试
       |
       +-- 5xx 服务端错误
       |    +-- 500 -- 重试 3 次，仍失败则告警
       |    +-- 502 / 503 -- 网关错误，重试 3 次
       |    +-- 504 -- 超时，检查超时设置
       |
       +-- 网络错误
            +-- 连接超时 -- 重试
            +-- 连接断开 -- 重试
"""
        print(tree)
