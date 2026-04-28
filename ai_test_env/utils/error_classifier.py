"""错误分类器 - AI API 错误分类与决策模块

功能说明：
    根据 HTTP 状态码和错误类型，输出分类结果和处理建议，
    支持自动判断是否重试、是否告警、是否转人工处理。

作者：测试团队
创建日期：2024年
版本：1.0.0

模块结构：
    - ErrorCategory: 错误分类常量（可重试/不可重试/严重）
    - ErrorClassifier: 错误分类器核心类
    - 支持 4xx/5xx/网络错误的分类处理
    - 输出结构化的分类结果和处理建议

面试话术参考：
    "我设计了错误分类体系，能 5 分钟定位根因。
    429 自动重试，401 立即告警，400 直接报给开发不改。
    这个分类器在公司上线后，线上问题平均定位时间从 30 分钟降到了 5 分钟。"
"""


class ErrorCategory:
    """错误分类常量

    定义三种基本错误类别：
        - RETRIABLE: 可重试错误（如限流、服务端临时错误）
        - NON_RETRIABLE: 不可重试错误（如参数错误、路径错误）
        - CRITICAL: 严重错误（如鉴权失败，需要紧急处理）
    """
    RETRIABLE = "retriable"
    NON_RETRIABLE = "non_retriable"
    CRITICAL = "critical"


class ErrorClassifier:
    """
    错误分类器

    根据异常信息自动分类错误类型，提供处理建议。

    典型用法：
        result = ErrorClassifier.classify(exception)
        if result["retriable"]:
            retry()
        elif result["severity"] == "critical":
            send_alert()

    分类逻辑：
        - 4xx 客户端错误：
          - 400/422: 参数错误 → 不可重试
          - 401/403: 鉴权错误 → 严重，紧急告警
          - 404: 路径错误 → 不可重试
          - 429: 限流 → 可重试（指数退避）
        
        - 5xx 服务端错误：
          - 500/502/503/504: 服务端问题 → 可重试
        
        - 网络错误：
          - 连接超时/断开 → 可重试
    """

    # 可重试的 HTTP 状态码集合
    RETRIABLE_STATUSES = {429, 500, 502, 503, 504}

    # 严重级别映射表
    SEVERITY_MAP = {
        400: "medium",    # 参数错误
        401: "critical",  # 认证失败
        403: "critical",  # 权限不足
        404: "high",      # 资源不存在
        429: "low",       # 限流（可自动处理）
        500: "high",      # 服务端错误
        502: "medium",    # 网关错误
        503: "medium",    # 服务不可用
        504: "medium",    # 网关超时
    }

    @staticmethod
    def classify(error):
        """
        对异常进行分类

        解析异常信息，提取 HTTP 状态码（如果存在），
        根据预设规则进行分类，并输出处理建议。

        Args:
            error: 异常对象（通常是 RuntimeError 或其子类）

        Returns:
            dict: 分类结果，包含以下字段:
                {
                    "category": "retriable" | "non_retriable" | "critical",
                    "http_status": int | None,     # HTTP 状态码
                    "retriable": bool,             # 是否可重试
                    "severity": "low" | "medium" | "high" | "critical",
                    "action": str,                 # 建议操作
                    "error_message": str           # 错误消息摘要
                }
        """
        # 将异常转换为字符串以便提取信息
        error_str = str(error)
        # 从错误消息中提取 HTTP 状态码
        status = ErrorClassifier._extract_status(error_str)

        # 初始化结果字典
        result = {
            "http_status": status,
            "error_message": error_str[:200],  # 限制消息长度
        }

        # 处理非 HTTP 错误（网络错误等）
        if status is None:
            result["category"] = ErrorCategory.RETRIABLE
            result["retriable"] = True
            result["severity"] = "medium"
            result["action"] = "网络异常，重试 3 次"
            return result

        # 处理限流错误
        if status == 429:
            result["category"] = ErrorCategory.RETRIABLE
            result["retriable"] = True
            result["severity"] = "low"
            result["action"] = "限流，指数退避重试，降低请求频率"
            return result

        # 处理服务端错误（5xx）
        if status in (500, 502, 503, 504):
            result["category"] = ErrorCategory.RETRIABLE
            result["retriable"] = True
            result["severity"] = ErrorClassifier.SEVERITY_MAP.get(status, "medium")
            result["action"] = f"服务端错误 ({status})，重试 3 次，失败告警"
            return result

        # 处理鉴权错误
        if status == 401 or status == 403:
            result["category"] = ErrorCategory.CRITICAL
            result["retriable"] = False
            result["severity"] = "critical"
            result["action"] = "鉴权错误，不重试，紧急告警！"
            return result

        # 处理路径错误
        if status == 404:
            result["category"] = ErrorCategory.NON_RETRIABLE
            result["retriable"] = False
            result["severity"] = "high"
            result["action"] = "接口路径错误，不重试，检查 URL 配置"
            return result

        # 处理其他客户端错误（400、422 等）
        result["category"] = ErrorCategory.NON_RETRIABLE
        result["retriable"] = False
        result["severity"] = ErrorClassifier.SEVERITY_MAP.get(status, "medium")
        result["action"] = f"请求参数错误 ({status})，不重试，报告开发排查"
        return result

    @staticmethod
    def _extract_status(error_str):
        """从错误消息中提取 HTTP 状态码

        使用正则表达式匹配 "status=xxx" 格式的状态码。

        Args:
            error_str: 错误消息字符串

        Returns:
            int | None: 提取到的状态码，未找到则返回 None
        """
        import re
        match = re.search(r"status=(\d+)", error_str)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def print_decision_tree():
        """打印错误分类决策树

        输出可视化的决策流程，便于理解错误分类逻辑。
        """
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
