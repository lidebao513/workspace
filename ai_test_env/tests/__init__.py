"""测试模块初始化文件

功能说明：
    定义测试模块的公共配置和工具函数，支持测试套件的组织和运行。

作者：测试团队
创建日期：2024年
版本：1.0.0

测试文件结构：
    - test_params.py: 参数边界测试
    - test_request_format.py: 请求格式验证测试
    - test_response_baseline.py: 响应结构验证与 Token 基线测试
"""

# 测试配置常量
TEST_TIMEOUT = 60  # 测试超时时间（秒）
RETRY_COUNT = 3    # 重试次数
