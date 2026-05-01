# Day 29 — CI 配置 + README

## 学习目标

1. 理解 GitHub Actions 的工作原理，学会编写 YAML 配置文件
2. 掌握矩阵测试配置，学会在 CI 中测试多版本 Python
3. 理解 Secrets 管理机制，学会安全地存储敏感信息
4. 掌握测试门禁策略，学会设置 BLOCKING/MANDATORY/SILENT 等不同级别的门禁
5. 学会编写高质量的 README 文档

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

**Q: 矩阵测试的优势是什么？为什么要测试多个 Python 版本？**
A: 矩阵测试可以用很少的配置代码覆盖多个环境。测试多个 Python 版本是为了确保代码兼容性——用户可能用不同版本的 Python，我们需要保证在所有支持的版本上都能正常工作。

**Q: 测试门禁策略中，BLOCKING、MANDATORY、SILENT 有什么区别？**
A: BLOCKING 会阻止 PR 合并，是最严格的门禁；MANDATORY 必须通过但可跳过紧急发布；SILENT 仅通知不阻塞。我会把冒烟测试设为 BLOCKING，性能测试设为 SILENT。

## 七、代码示例

### GitHub Actions 完整配置

```yaml
name: AI Test Engine CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-html
    
    - name: Run tests
      env:
        DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
      run: |
        python -m pytest tests/ \
          --html=report-${{ matrix.python-version }}.html \
          --self-contained-html \
          -v
    
    - name: Upload test report
      uses: actions/upload-artifact@v4
      with:
        name: test-report-${{ matrix.python-version }}
        path: report-${{ matrix.python-version }}.html
        if-no-files-found: warn
```

### README.md 模板

```markdown
# AI Test Engine

> 一个用于 AI API 测试的综合测试框架，覆盖质量评估、安全测试、性能压测等维度。

## Quick Start

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 运行冒烟测试
python -m pytest tests/smoke/ -v

# 运行全部测试
python -m pytest tests/ -v --html=report.html
```

## Features

- **分层架构**: config/core/tests 三层分离，便于维护和扩展
- **质量评估**: 5 维评分体系（完整性、相关性、连贯性、一致性、简洁性）
- **安全测试**: 9 种 Prompt Injection 检测 + 6 种健壮性扰动
- **性能测试**: 并发压测、P95/P99 指标、熔断器保护
- **CI/CD**: GitHub Actions 矩阵测试 + 测试门禁
- **Token 审计**: 输入/输出分开计费 + 异常检测

## Project Structure

```
ai_test_engine/
├── config/               # 配置层
│   └── settings.py       # 配置管理
├── core/                 # 核心层
│   ├── client.py         # API 客户端
│   ├── error_handler.py  # 错误处理
│   └── key_manager.py    # Key 管理
├── tests/                # 测试层
│   ├── smoke/            # 冒烟测试
│   ├── quality/          # 质量评估测试
│   ├── security/         # 安全测试
│   ├── performance/      # 性能测试
│   └── test_integration.py # 集成测试
├── .github/workflows/    # CI 配置
├── .env.example          # 环境变量模板
├── requirements.txt      # 依赖列表
└── README.md             # 项目说明
```

## Configuration

| 参数 | 默认值 | 说明 |
|------|--------|------|
| DEEPSEEK_API_KEY | - | DeepSeek API Key |
| API_BASE_URL | https://api.deepseek.com | API 基础地址 |
| MODEL_NAME | deepseek-chat | 模型名称 |
| MAX_RETRIES | 3 | 最大重试次数 |
| TIMEOUT | 30 | 请求超时时间（秒） |
| MAX_TOKENS | 4096 | 最大 Token 数 |
| TEMPERATURE | 0.7 | 温度参数 |

## CI Badge

[![CI](https://github.com/your-username/ai_test_engine/actions/workflows/test.yml/badge.svg)](https://github.com/your-username/ai_test_engine/actions/workflows/test.yml)

## License

MIT License
```

## 八、产出物

- `.github/workflows/test.yml`
- `README.md`
- `requirements.txt`
- `.env.example`

## 九、练习题

1. **基础题：** 在 GitHub Actions 配置中添加一个新的步骤，在测试前运行 `flake8` 代码检查。

2. **进阶题：** 修改 CI 配置，添加一个单独的 `deploy` job，只有在 `main` 分支测试通过后才执行。

3. **挑战题：** 为项目编写一个完整的 `.env.example` 文件，包含所有必要的环境变量及其说明。

## 十、自检清单

- [ ] workflow 覆盖 3 个 Python 版本
- [ ] 测试报告作为 artifact 上传
- [ ] README 包含 Quick Start
- [ ] .env.example 不包含真实 Key
