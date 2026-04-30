# Day 29 — CI 配置 + README

## 一、引言

有了代码和测试，还差两个关键文件：CI（持续集成）让每次提交自动跑测试，README 让人一看就知道项目是什么。

## 二、前置知识讲解

### 2.1 什么是 GitHub Actions？

**一句话定义：** GitHub 自带的 CI/CD 工具，通过 `.yml` 文件定义触发条件、运行步骤、输出物。

**类比：** 工厂流水线——原料入库（push）、经过多个工位（steps）、质检（tests）、包装出厂（artifact）。

⚙️ YAML = Yet Another Markup Language，一种比 JSON 更易读的数据格式，缩进代表层级。

**代码片段：**
```yaml
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
```

**面试话术：** "矩阵测试是 CI 中性价比最高的配置——3 个 Python 版本 = 3 倍覆盖率，但配置代码只多 3 行。"

### 2.2 Secrets 管理

**一句话定义：** 敏感信息（API Key）不在代码明文存储，而是放在 GitHub Settings → Secrets，运行时通过 `${{ secrets.NAME }}` 注入。

**面试话术：** "`.env` 只在本地用，CI 环境用 Secrets。这是安全底线——DEEPSEEK_API_KEY 暴露出去每分钟烧掉 100 块钱。"

### 2.3 测试门禁（Test Gate）

**一句话定义：** CI 中某一步失败后阻止后续操作（如合入 PR）的机制。

**场景：** smoke 失败→不允许合入 PR（BLOCKING）；performance 失败→只通知不阻塞（SILENT）。

## 三、需求分析

- GitHub Actions workflow: 矩阵测试 + 报告上传
- README: 7 个标准节（标题/Quick Start/Features/结构/配置/面试话术/CI badge）

## 四、代码说明

### .github/workflows/test.yml
- push/PR to main 触发
- Python 3.9/3.10/3.11 矩阵
- install → test → upload report
- DEEPSEEK_API_KEY 通过 Secrets 传入
- always() 保证生成报告即使测试失败

### README.md
- 一句话项目描述
- pip install + cp .env.example + pytest
- Features 6 个点的能力清单
- 项目结构树
- 配置表（参数/默认值/说明）
- 面试话术

## 五、工作场景

- PR 提交后自动跑测试
- 新人看 README 就能上手
- 报告作为 CI artifact 存档

## 六、面试问题

**Q: CI 中如何处理真实 API 调用？没 Key 怎么办？**
A: 我的测试全都有 Mock 模式——跑 CI 不需要真实 API Key。Secrets 是可选的，不传 Key 就只跑非 API 测试。真实 Key 只用在集成测试阶段手动触发。

**Q: pytest-html 生成的报告有什么用？**
A: 可视化——主管不是每次都有空看终端输出。HTML 报告里通过率、失败堆栈、耗时一目了然。还支持 self-contained HTML，不用加载外部资源。

## 七、产出物

- `.github/workflows/test.yml`
- `README.md`
- `requirements.txt`
- `.env.example`

## 八、自检清单

- [ ] workflow 覆盖 3 个 Python 版本
- [ ] 测试报告作为 artifact 上传
- [ ] README 包含 Quick Start
- [ ] .env.example 不包含真实 Key
