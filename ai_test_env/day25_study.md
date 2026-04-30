# Day 25 — 生产级错误体系

## 一、今日目标

> 学会设计分级异常体系：FATAL / ERROR / WARN / INFO 四级，配合自动分类器和处理规则。

- 理解 5 种 AppError 子类场景
- 掌握 ErrorClassifier 自动分类
- 学会 should_retry / should_alert / is_fatal 判断

---

## 二、异常分级

| 级别 | 子类 | 处理动作 | 示例 |
|------|------|----------|------|
| FATAL | ConfigError, AuthError | STOP | 缺少 API Key / 认证失败 |
| ERROR | APIError | RETRY_THEN_ALERT | 500 / 超时 |
| WARN | RateLimitError, ValidationError | RETRY 或 LOG | 429限流 / 参数非法 |
| INFO | (通用异常) | LOG | 调试信息 |

### ErrorClassifier 自动映射

```python
class ErrorClassifier:
    @classmethod
    def classify(cls, error): ...
    @classmethod
    def should_retry(cls, error): ...
    @classmethod
    def should_alert(cls, error): ...
    @classmethod
    def is_fatal(cls, error): ...
```

通用异常映射：
- `ConnectionError` → ERROR / RETRY_THEN_ALERT
- `TimeoutError` → ERROR / RETRY_THEN_ALERT
- `ValueError` → WARN / LOG
- 未知 → ERROR / ALERT

---

## 三、运行验证

```
20 passed in 0.03s
```

---

## 四、面试话术

**设计思路：** "我设计的分级错误体系，目标是区分'该不该继续'。FATAL 直接终止，因为重试一万次也解决不了认证问题。WARN 只记录，因为参数校验失败不影响其他流程。"

**与重试/熔断的配合：** "ErrorClassifier 的 should_retry 接口直接对接 RetryEngine，FATAL 级错误跳过重试。should_alert 对接告警系统。三层联动：重试→熔断→告警。"
