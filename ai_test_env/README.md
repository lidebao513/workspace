# AI 测试环境 - Day 1

## 前置要求
- Python 3.8+
- DeepSeek API Key（注册 https://platform.deepseek.com 获取）

## 快速开始

```bash
# 1. 进入项目目录
cd ai_test_env

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# 4. 安装依赖
pip install openai python-dotenv

# 5. 配置 API Key
# 复制 .env.example 为 .env，填入你的 DeepSeek API Key

# 6. 运行冒烟测试
python smoke_test.py
```

## 文件说明

| 文件 | 说明 |
|:----|:----|
| `.env.example` | 环境变量模板 |
| `smoke_test.py` | 冒烟测试脚本（Day 1 产出） |
| `utils/api_client.py` | API 客户端封装 |
