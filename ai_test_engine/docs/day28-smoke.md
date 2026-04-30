# Day 28 — 冒烟测试：边界值 + 错误处理 + 消息格式

## 一、引言

冒烟测试是项目的第一道关口——不跑过冒烟，不进其它测试。为 `ai_test_engine` 建立 62 个冒烟测试用例，覆盖 API 参数的边界条件、4xx/5xx/网络错误、消息格式校验。

## 二、前置知识讲解

### 2.1 什么是边界值分析（BVA）？

**一句话定义：** 测试时重点验证取值范围的最小值、最大值、比最小少 1、比最大多 1 等边界。

**类比：** 限高 1.2 米的游乐设施——1.19 米能玩，1.20 米也能玩，1.21 米不行。边界最危险。

**代码：**
```python
# 测试 max_tokens 边界
max_tokens: 0, 1, 4096, -1
# 测试 temperature 边界
temperature: 0.0, 0.5, 1.0, 2.0, -0.5
```

**面试话术：** "80% 的 bug 发生在边界。temperature 传 -0.5 应该报错，传 0 应该稳定输出。如果 API 不校验边界，测试得替它兜底。"

### 2.2 HTTP 状态码分类

**一句话定义：** HTTP 响应码按首位数字分类：2xx 成功、4xx 客户端错误、5xx 服务端错误。

**面试话术：** "4xx 说明你的请求有问题（401 没权限、429 太频繁），5xx 说明服务端有问题（500 挂了、502 网关超时）。错误分级就是按这个分——4xx 的 429 轻量级 WARN，5xx 的 500 标记为 ERROR 需要告警。"

### 2.3 消息格式验证为什么重要？

**一句话定义：** AI API 对消息格式（role/content 结构）很敏感，格式错直接返回 400。

**面试话术：** "我见过最搞笑的 bug——测试脚本把 'user' 拼成 'uaser'，API 返回 400，排查了 20 分钟才发现。消息格式测试必须在冒烟阶段就覆盖。"

## 三、需求分析

三个冒烟测试文件：
1. `test_boundary.py` — max_tokens/temperature/top_p 边界 + 消息格式
2. `test_errors.py` — 4xx/5xx/网络/配置/校验五类
3. `test_connectivity.py` — 核心模块可用性

## 四、代码说明

### test_boundary.py
- TestMaxTokensBoundary: 0/1/4096/-1
- TestTemperatureBoundary: 0/0.5/1.0/2.0/-0.5
- TestTopPBoundary: 0/0.5/1.0/-0.1
- TestMessageFormat: 有效/无效角色、空内容、超长内容、多轮结构

### test_errors.py
- Test4xxErrors: 400/401/403/429
- Test5xxErrors: 500/502/503
- TestNetworkErrors: timeout/connection_refused/reset
- TestConfigErrors: 缺少 Key/无效 Base URL/错误模型名
- TestValidationErrors: 类型/范围/必填字段

### test_connectivity.py
- TestSettings: 默认值/校验/序列化
- TestAIEngineClient: 初始化/提取方法
- TestErrorHandler: 分类/可重试/致命判断
- TestKeyManager: 轮换/降级/失败计数

## 五、运行结果

```
62 passed (connectivity: 26 + boundary: 20 + errors: 16)
```

## 六、工作场景

- 新 API 版本升级——跑冒烟测试确认参数格式没变
- 接入新模型——冒烟确认参数范围兼容
- 每次提交——冒烟在 CI 中作为 gate 门控

## 七、面试问题

**Q: 冒烟测试的标准是什么？应该测试多少用例？**
A: 冒烟的核心是"快速反馈"。我的标准是：如果冒烟不过，其它测试不用跑。62 个用例覆盖了最关键的参数和错误路径，跑 0.07 秒。

**Q: 如何处理 API Key 对冒烟测试的限制？**
A: 所有冒烟测试都是无 API 调用、纯逻辑测试。连通性测试不调真实 API，只验证参数构造是否正确。这是刻意设计的——让测试可以离线跑。

## 八、产出物

- `tests/smoke/test_boundary.py` — 20 个边界 + 格式测试
- `tests/smoke/test_errors.py` — 16 个错误分类测试
- `tests/smoke/test_connectivity.py` — 26 个核心可用性测试

## 九、自检清单

- [ ] 覆盖 max_tokens 0/1/4096/-1
- [ ] 覆盖 temperature 0/0.5/1.0/2.0/-0.5
- [ ] 覆盖 top_p 0/0.5/1.0/-0.1
- [ ] 覆盖 4xx/5xx/网络/配置/校验五类错误
- [ ] 消息格式：有效角色、无效角色、空内容、多轮

## 十、运行验证

```bash
cd ai_test_engine
python -m pytest tests/smoke/ -v
```
