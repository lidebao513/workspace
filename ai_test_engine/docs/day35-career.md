# Week 8 Day 35 — 薪资谈判 + 求职策略

## 学习目标

1. 了解上海 AI 测试工程师的薪资范围，学会评估自己的市场价值
2. 掌握目标公司分类方法，学会制定求职策略
3. 学会提炼简历亮点，将项目经验转化为竞争力
4. 掌握薪资谈判技巧，学会争取合理薪酬
5. 学会制定投递计划，提高求职效率

> 基于 `shanghai_ai_test_jd_requirements.md` 的薪资参考数据。
> 数据采集时间：26-04-28。实际薪资请按最新市场情况调整。

---

## 上海 AI 测试工程师薪资范围

| 级别 | 经验 | 月薪范围 |
|------|------|----------|
| 初级 | 1-3 年 | 12K-18K |
| 中级 | 3-5 年 | 18K-28K |
| 高级 | 5+ 年 | 28K-40K |
| 架构/Leader | 8+ 年 | 40K-55K |

注：外企通常高 15-30%，但公积金比例也更高（12% vs 5-7%）。

---

## 目标公司分类

### Tier 1：外企（薪资高、WLB 好、英语要求）
- 微软（上海紫竹）
- SAP（上海）
- Intel（上海）
- Booking（上海）
- 汇丰科技（上海/西安）

### Tier 2：金融/FinTech（薪资中高、福利好）
- 蚂蚁集团
- 京东科技
- 平安科技
- 招行信用卡中心
- 陆金所

### Tier 3：AI 公司（技术前沿、股票/期权价值高）
- 字节跳动（Flow/火山引擎）
- 百度（飞桨/智能云）
- MiniMax
- 月之暗面
- 智谱 AI
- DeepSeek（深度求索）

### Tier 4：互联网大厂（平台大、但竞争激烈）
- 美团
- 拼多多
- 携程
- B 站

---

## 简历亮点提炼

从 `ai_test_engine` 项目中可以提取的关键词：

1. **分层测试框架设计** — config/core/tests 三层架构，从冒烟到性能全覆盖
2. **多维度 AI 测试能力** — 质量评估（5 维评分）、安全注入（9 种）、性能压测（P95/P99）
3. **CI/CD 集成** — GitHub Actions + 多 Python 版本矩阵 + 门禁策略
4. **错误体系设计** — 四级 FATAL/ERROR/WARN/INFO + 自动分类 + 告警规则
5. **Auto-Retry 与熔断** — 指数退避 + 三态熔断器 + Key 降级策略
6. **Token 成本监控** — 输入/输出分开计费 + 日基线 + 环比异常检测

---

## 薪资谈判脚本

### 场景：HR 问期望薪资

**不要先说数字。** 先反问：

> "我看贵公司在 AI 测试领域也有布局，想先了解一下这个岗位的预算范围，以及薪资结构是怎样的？"

### 如果 HR 非让你先说：

```
"根据我的项目经验和对市场的了解，我期望的月薪范围在 XX 到 YY 之间。
我搭建了完整的 AI 测试框架，从 API 连通性到生产级错误体系，
这些经验对贵公司应该是比较有直接价值的。

不过薪资并不是唯一的考虑因素——比如团队的技术氛围、成长空间、
以及福利体系（比如公积金比例、期权）也是我很看重的。"
```

### 拿到 Offer 后的谈判话术：

```
"感谢 Offer。我对贵公司很感兴趣，但在薪资方面，
我手上还有其他选择。如果贵公司能在 XX 的基础上再上浮 10-15%，
我可以很快做出决定。"
```

---

## 投递策略

### 第一阶段：练手（第 1-2 周）
- 投递 Tier 3-4 公司（非首选但面试流程快）
- 收集真实面试题反馈
- 测试自己的薪资谈判能力

### 第二阶段：核心（第 3-4 周）
- 投递 Tier 1-2 公司
- 根据第一阶段反馈优化回答话术
- 集中约面（控制节奏，避免撞车）

### 第三阶段：决策（第 5-6 周）
- 对比 Offer（薪资/公积金/期权/距离/成长）
- 谈判收尾

---

## 面试 Checklist

- [ ] ai_test_engine README 能 3 分钟讲清楚架构
- [ ] 能随口说出项目关键数据（161 tests, 0.5s 跑完）
- [ ] 能现场画项目结构图（白板/纸）
- [ ] 准备好项目链接/github/演示
- [ ] 10 道高频题能自然说出来（不背稿）
- [ ] 准备好反问面试官的问题（团队/技术栈/质量指标）

---

## 可反问面试官的问题

1. "贵公司目前 AI 测试的流程是怎样的？自研工具还是买商业方案？"
2. "AI 测试在你们团队是独立岗位还是 QA 兼做？"
3. "你们用什么模型？如何评估回复质量？"
4. "有没有遇到过因为 AI 输出问题导致的生产事故？"
5. "团队的技术栈是什么？测试覆盖率的目标是多少？"

---

## 代码示例

### 薪资计算器与求职追踪工具

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

@dataclass
class SalaryRange:
    """薪资范围"""
    level: str
    experience: str
    min_salary: int  # K/月
    max_salary: int  # K/月
    
    def calculate_expected(self, years: int, performance: float = 1.0) -> int:
        """计算期望薪资"""
        base = (self.min_salary + self.max_salary) // 2
        return int(base * performance)

@dataclass
class JobApplication:
    """求职申请记录"""
    company: str
    tier: str
    position: str
    status: str  # applied/interviewing/offered/rejected
    salary_offer: Optional[int] = None  # K/月
    notes: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

class CareerManager:
    """职业管理工具"""
    
    # 上海 AI 测试薪资基准
    SHANGHAI_SALARY_RANGES = [
        SalaryRange("初级", "1-3年", 12, 18),
        SalaryRange("中级", "3-5年", 18, 28),
        SalaryRange("高级", "5+年", 28, 40),
        SalaryRange("架构/Leader", "8+年", 40, 55)
    ]
    
    def __init__(self):
        self.applications: List[JobApplication] = []
    
    def estimate_salary(self, experience_years: int, level: str = None) -> dict:
        """估算薪资范围"""
        # 根据经验确定级别
        if level is None:
            if experience_years < 3:
                level = "初级"
            elif experience_years < 5:
                level = "中级"
            elif experience_years < 8:
                level = "高级"
            else:
                level = "架构/Leader"
        
        for sr in self.SHANGHAI_SALARY_RANGES:
            if sr.level == level:
                return {
                    "level": sr.level,
                    "experience": sr.experience,
                    "min": sr.min_salary,
                    "max": sr.max_salary,
                    "expected": sr.calculate_expected(experience_years)
                }
        
        return {}
    
    def add_application(self, company: str, tier: str, position: str) -> None:
        """添加求职申请"""
        self.applications.append(JobApplication(
            company=company,
            tier=tier,
            position=position,
            status="applied"
        ))
    
    def update_status(self, company: str, status: str, 
                     salary_offer: Optional[int] = None, notes: str = "") -> bool:
        """更新申请状态"""
        for app in self.applications:
            if app.company == company:
                app.status = status
                app.salary_offer = salary_offer
                app.notes = notes
                return True
        return False
    
    def get_status_report(self) -> dict:
        """生成求职进度报告"""
        status_counts = {}
        total_applied = len(self.applications)
        offers = [a for a in self.applications if a.status == "offered"]
        avg_offer = sum(o.salary_offer for o in offers if o.salary_offer) / len(offers) if offers else 0
        
        for app in self.applications:
            status_counts[app.status] = status_counts.get(app.status, 0) + 1
        
        return {
            "total_applied": total_applied,
            "status_counts": status_counts,
            "offer_count": len(offers),
            "avg_offer": round(avg_offer, 1) if avg_offer else 0,
            "conversion_rate": round(len(offers) / total_applied * 100, 2) if total_applied else 0
        }
    
    def generate_negotiation_script(self, current_offer: int, expected_min: int) -> str:
        """生成薪资谈判脚本"""
        if current_offer >= expected_min:
            return f"当前 Offer {current_offer}K 已达到期望，可接受或小幅争取。"
        
        gap = expected_min - current_offer
        percentage = round(gap / current_offer * 100, 1)
        
        return f"""薪资谈判脚本：

当前 Offer: {current_offer}K
期望薪资: {expected_min}K
差距: {gap}K ({percentage}%)

推荐话术：
"感谢贵公司的 Offer。我对这个机会非常感兴趣，
但考虑到我的经验和技能，我期望的薪资在 {expected_min}K 左右。
不知道贵公司是否有调整的空间？"

备选方案：
如果对方无法满足薪资：
"如果薪资方面确实有困难，能否考虑其他福利，
比如更高的年终奖金、更多的年假或者期权？"
"""

# 使用示例
if __name__ == "__main__":
    manager = CareerManager()
    
    # 估算薪资
    salary = manager.estimate_salary(5)
    print("薪资估算:", salary)
    
    # 添加求职申请
    manager.add_application("DeepSeek", "Tier 3", "AI测试工程师")
    manager.add_application("蚂蚁集团", "Tier 2", "AI质量工程师")
    manager.add_application("微软", "Tier 1", "Software Test Engineer")
    
    # 更新状态
    manager.update_status("DeepSeek", "offered", 32, "base:32K, 14薪")
    manager.update_status("蚂蚁集团", "interviewing", notes="二面完成")
    
    # 获取报告
    report = manager.get_status_report()
    print("\n求职进度报告:")
    print(f"  总投递: {report['total_applied']}")
    print(f"  各状态分布: {report['status_counts']}")
    print(f"  Offer数量: {report['offer_count']}")
    print(f"  平均Offer: {report['avg_offer']}K")
    
    # 生成谈判脚本
    script = manager.generate_negotiation_script(32, 35)
    print("\n" + script)
```

---

## 练习题

1. **基础题：** 使用 `CareerManager` 工具，添加 5 家目标公司的投递记录，并更新它们的状态。

2. **进阶题：** 假设你有 3 年 AI 测试经验，使用薪资计算器估算你的期望薪资，并生成一份完整的薪资谈判脚本。

3. **挑战题：** 扩展 `CareerManager` 类，添加以下功能：
   - 支持记录面试时间和反馈
   - 支持按公司 Tier 分组统计
   - 添加投递阶段提醒（如超过 7 天无回复提醒跟进）

---

## 自检清单

- [ ] 知道上海 AI 测试工程师各级别薪资范围
- [ ] 熟悉目标公司的分级和各自特点
- [ ] 准备好薪资谈判三板斧脚本
- [ ] 想好反问面试官的问题（不背稿）
- [ ] 完成面试 Checklist 所有项
