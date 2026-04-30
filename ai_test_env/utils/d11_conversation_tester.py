"""
多轮对话上下文测试模块

功能：模拟连续 N 轮对话，验证 AI 模型的信息保持能力。
包括上下文召回率、关键实体传递率、Token 消耗分析和会话历史管理。

面试话术：
    "多轮对话测试是我在做金融客服场景时发现的痛点。
    模型在小样本对话中表现很好，但到第 5 轮以后
    就开始"断片"——忘记用户之前说的关键信息。
    我们设计了一套上下文测试框架，量化了信息保持率，
    发现大多数通用模型在第 10 轮后关键实体召回率
    下降到 60% 以下。金融场景我们强制做了上下文摘要。"
"""
import json
from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from copy import deepcopy


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class Turn:
    """单轮对话"""
    role: str                    # user / assistant
    content: str                 # 本轮内容
    tokens: int = 0              # 本轮消耗 Token（可选）
    latency_ms: float = 0.0      # 本轮延迟（可选）

    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content[:30]}


@dataclass
class Conversation:
    """一次完整的对话会话"""
    turns: List[Turn] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0

    def add_turn(self, role: str, content: str, tokens: int = 0, latency_ms: float = 0.0):
        self.turns.append(Turn(role, content, tokens, latency_ms))
        self.total_tokens += tokens
        self.total_latency_ms += latency_ms

    @property
    def length(self) -> int:
        return len(self.turns)

    def summary(self) -> Dict:
        return {
            "total_turns": self.length,
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "avg_tokens_per_turn": round(self.total_tokens / max(self.length, 1), 1),
            "avg_latency_per_turn": round(self.total_latency_ms / max(self.length, 1), 1),
        }

    def to_messages(self) -> List[Dict]:
        """转换为 OpenAI API 的 messages 格式"""
        return [{"role": t.role, "content": t.content} for t in self.turns]


@dataclass
class ContextTestResult:
    """多轮对话上下文测试结果"""
    conversation: Conversation
    key_info: Dict[str, str]           # 第 1 轮注入的关键信息 {key: value}
    key_recall_later: Dict[str, str]   # 后续轮中召回的 {key: value}
    recall_rate: float                 # 召回率 (0.0 - 1.0)
    turns_until_forget: int            # 第几轮开始遗忘（-1 = 未遗忘）
    token_growth_rate: float           # Token 增长率（每轮增加多少）
    conclusion: str = ""


# ---------------------------------------------------------------------------
# 多轮对话上下文测试器
# ---------------------------------------------------------------------------

class ConversationTester:
    """
    多轮对话上下文测试器

    能力：
    1. 自动构造 N 轮对话脚本
    2. 在特定轮次注入关键信息
    3. 在后续轮次验证信息保持
    4. 分析 Token 消耗趋势

    用法（离线模式）：
        tester = ConversationTester()

        # 构造对话历史
        conv = Conversation()
        conv.add_turn("user", "你好，我叫张三")
        conv.add_turn("assistant", "你好张三！")
        conv.add_turn("user", "我的银行卡尾号是 8888")
        conv.add_turn("assistant", "收到，尾号 8888")
        conv.add_turn("user", "我刚才说我的名字是什么？")  # 验证轮

        result = tester.analyze_context(
            key_info={"name": "张三", "card_last4": "8888"},
            recall_responses={"name": "张三", "card_last4": "8888"},  # 模型在这个验证轮的回复
        )
        print(f"召回率: {result.recall_rate}")
    """

    def __init__(self):
        self._history: List[Dict] = []

    # ------------------------------------------------------------------
    # 构造对话脚本
    # ------------------------------------------------------------------

    def build_conversation_script(
        self,
        key_info: Dict[str, str],
        context_turns_before: int = 2,   # 注入信息前的寒暄轮次
        context_turns_after: int = 3,    # 注入信息后的干扰轮次
        verification_delays: List[int] = None,  # 在第几轮验证（相对注入轮）
    ) -> List[Dict]:
        """
        构造多轮对话脚本。

        典型的"注入 → 干扰 → 验证"三部曲：

        轮次 1-2: 寒暄（无关对话）
        轮次 3:   注入关键信息（如"我叫张三，卡号 8888"）
        轮次 4-6: 干扰对话（聊天气、问功能）
        轮次 7:   第 1 次验证（"我名字叫什么？"）
        轮次 8:   第 2 次验证（"我卡号多少？"）

        返回消息列表：
            [{"role": "user", "content": "..."},
             {"role": "assistant", "content": "..."},
             ...]
        """
        verification_delays = verification_delays or [1, 3, 5]

        script = []
        keys_formatted = ", ".join(f"{k}={v}" for k, v in key_info.items())

        # 阶段 1：寒暄
        greetings = [
            "你好！今天天气不错。",
            "是的，请问有什么可以帮您？",
            "我想咨询一下你们的产品。",
            "好的，请说。",
            "你们公司主要做什么的？",
        ]
        for i in range(context_turns_before):
            if i < len(greetings):
                script.append({"role": "user", "content": greetings[i],
                               "_tag": "greeting", "_turn_id": i + 1})
                script.append({"role": "assistant", "content": f"感谢您的提问（回复{i+1}）。",
                               "_tag": "assistant_response", "_turn_id": i + 1})

        # 阶段 2：注入关键信息
        injection_turn = context_turns_before + 1
        script.append({
            "role": "user",
            "content": f"我来说说我的信息，{keys_formatted}，你记好了。",
            "_tag": "info_injection",
            "_key_info": key_info,
            "_turn_id": injection_turn,
        })
        script.append({
            "role": "assistant",
            "content": f"好的，我已经记住了您的信息（回复{injection_turn}）。",
            "_tag": "assistant_response",
            "_turn_id": injection_turn,
        })

        # 阶段 3：干扰对话
        distractors = [
            "你们有没有手机 App？",
            "周末你们上班吗？",
        ]
        start_turn = injection_turn + 1
        for i in range(context_turns_after):
            if i < len(distractors):
                tid = start_turn + i
                script.append({"role": "user", "content": distractors[i],
                               "_tag": "distractor", "_turn_id": tid})
                script.append({"role": "assistant", "content": f"关于这个问题的回答（回复{tid}）。",
                               "_tag": "assistant_response", "_turn_id": tid})

        # 阶段 4：验证轮
        verification_start = start_turn + len(distractors)
        questions = self._build_verification_questions(key_info)
        for i, delay in enumerate(verification_delays):
            if i < len(questions):
                tid = verification_start + i
                script.append({
                    "role": "user",
                    "content": questions[i],
                    "_tag": "verification",
                    "_expected": key_info,
                    "_turn_id": tid,
                })
                # assistant 回复留空（由模型生成）

        return script

    def _build_verification_questions(self, key_info: Dict[str, str]) -> List[str]:
        """根据注入的关键信息生成验证问题"""
        questions = []
        for key, value in key_info.items():
            # 中文场景
            key_labels = {
                "name": "我的名字",
                "phone": "我的手机号",
                "card_last4": "我的银行卡尾号",
                "address": "我的地址",
                "id_number": "我的身份证号",
                "email": "我的邮箱",
                "company": "我的公司",
                "account": "我的账号",
                "amount": "我的金额",
            }
            label = key_labels.get(key, key)
            questions.append(f"我刚才说的{label}是什么？")
        return questions

    # ------------------------------------------------------------------
    # 分析接口
    # ------------------------------------------------------------------

    def analyze_context(
        self,
        key_info: Dict[str, str],               # 注入的关键信息
        recall_responses: Dict[str, str],       # 模型在验证轮中对各 key 的回复
        conversation: Optional[Conversation] = None,  # 完整的对话记录（可选）
        verification_turn: int = 0,              # 在第几轮验证的
    ) -> ContextTestResult:
        """
        分析上下文保持率。

        参数：
            key_info: 注入的关键信息 {"name": "张三", "card_last4": "8888"}
            recall_responses: 模型在验证轮中回复中包含的正确值
                              {"name": "张三", "card_last4": "6666"}
                              → name 正确，card_last4 错误
            conversation: 完整对话（可选）
            verification_turn: 在第几轮验证的

        返回：
            ContextTestResult
        """
        if not key_info:
            return ContextTestResult(
                conversation=conversation or Conversation(),
                key_info={},
                key_recall_later={},
                recall_rate=1.0,
                turns_until_forget=-1,
                token_growth_rate=0.0,
                conclusion="无关键信息注入",
            )

        total_keys = len(key_info)
        correct_keys = 0
        key_recall_later = {}

        for key, expected_value in key_info.items():
            actual_value = recall_responses.get(key, "")
            # 跳过空值（模型没提到这个信息）
            if not actual_value:
                key_recall_later[key] = f"[遗忘] 期望={expected_value}, 实际=空"
            # 完全匹配
            elif actual_value == expected_value:
                correct_keys += 1
                key_recall_later[key] = actual_value
            elif expected_value in actual_value:
                # 包含匹配（模型可能加了额外描述）
                correct_keys += 1
                key_recall_later[key] = actual_value
            else:
                key_recall_later[key] = f"[遗忘] 期望={expected_value}, 实际={actual_value}"

        recall_rate = correct_keys / total_keys if total_keys > 0 else 1.0

        # 判断在哪一轮开始遗忘
        turns_until_forget = -1 if recall_rate >= 1.0 else verification_turn

        # Token 增长率
        token_growth_rate = 0.0
        if conversation and conversation.length > 1:
            # 计算每轮增加的 Token 数变化趋势
            turn_tokens = []
            cumulative = 0
            for t in conversation.turns:
                if t.tokens > 0:
                    cumulative += t.tokens
                    turn_tokens.append(cumulative)
            if len(turn_tokens) >= 2:
                # 用最后几轮算增长率
                recent = turn_tokens[-min(3, len(turn_tokens)):]
                if len(recent) >= 2:
                    token_growth_rate = round(
                        (recent[-1] - recent[0]) / max(len(recent) - 1, 1), 1
                    )

        # 结论
        if recall_rate >= 1.0:
            conclusion = f"第 {verification_turn} 轮验证，全部 {total_keys} 个关键信息保持完好"
        elif recall_rate >= 0.8:
            conclusion = f"第 {verification_turn} 轮验证，召回率 {recall_rate:.0%}，大部分信息保持"
        elif recall_rate >= 0.5:
            conclusion = f"第 {verification_turn} 轮验证，召回率 {recall_rate:.0%}，约半数信息遗忘"
        else:
            conclusion = f"第 {verification_turn} 轮验证，召回率 {recall_rate:.0%}，严重遗忘"

        result = ContextTestResult(
            conversation=conversation or Conversation(),
            key_info=key_info,
            key_recall_later=key_recall_later,
            recall_rate=recall_rate,
            turns_until_forget=turns_until_forget,
            token_growth_rate=token_growth_rate,
            conclusion=conclusion,
        )

        self._history.append(self._result_to_dict(result))
        return result

    def _result_to_dict(self, result: ContextTestResult) -> Dict:
        return {
            "key_info": dict(result.key_info),
            "recall_rate": result.recall_rate,
            "turns_until_forget": result.turns_until_forget,
            "conclusion": result.conclusion,
        }

    # ------------------------------------------------------------------
    # 遗忘曲线测试
    # ------------------------------------------------------------------

    def forget_curve(
        self,
        key_info: Dict[str, str],
        api_func: Callable,
        delays: List[int] = None,
        context_turns_before: int = 2,
        context_turns_after: int = 3,
    ) -> List[ContextTestResult]:
        """
        遗忘曲线测试：在不同轮次间隔后验证模型是否还记得。

        例如 delays=[1, 3, 5, 10] 表示在注入信息后的
        第 1、3、5、10 轮分别问一次验证问题，观察召回率趋势。

        返回：每个 delay 点的 ContextTestResult 列表
            → 可绘制"召回率 vs 间隔轮次"曲线
        """
        delays = delays or [1, 3, 5, 10]
        results = []

        for delay in delays:
            # 构造脚本（注入 + delay 轮干扰 + 验证）
            script = self.build_conversation_script(
                key_info=key_info,
                context_turns_before=context_turns_before,
                context_turns_after=delay,
                verification_delays=[0],  # 立即验证
            )

            # 找验证轮
            verification_msg = None
            for msg in script:
                if msg.get("_tag") == "verification":
                    verification_msg = msg
                    break

            if not verification_msg:
                continue

            # 模拟提取模型回复中的关键信息
            # 离线模式下由外部填写 recall_responses
            # 这里只做构造，不实际调用 API

            # 占位：在测试中会用模拟数据填充
            results.append(None)

        return results

    # ------------------------------------------------------------------
    # 统计接口
    # ------------------------------------------------------------------

    def history(self) -> List[Dict]:
        return list(self._history)

    def reset(self):
        self._history = []


# ---------------------------------------------------------------------------
# 对话历史管理
# ---------------------------------------------------------------------------

class ConversationManager:
    """
    对话历史管理器

    管理多次对话会话的存储、读取和生命周期。
    可导出为 OpenAI API messages 格式。
    """

    def __init__(self):
        self._conversations: List[Conversation] = []

    def create_conversation(self) -> Conversation:
        conv = Conversation()
        self._conversations.append(conv)
        return conv

    def latest(self) -> Optional[Conversation]:
        return self._conversations[-1] if self._conversations else None

    def all(self) -> List[Conversation]:
        return list(self._conversations)

    def count(self) -> int:
        return len(self._conversations)

    def summary_all(self) -> List[Dict]:
        return [c.summary() for c in self._conversations]

    def export_messages(self, conversation: Conversation) -> List[Dict]:
        return conversation.to_messages()

    def token_trend(self) -> List[Dict]:
        """返回每轮对话的累计 Token 消耗趋势"""
        trends = []
        for conv in self._conversations:
            cumulative = 0
            points = []
            for i, turn in enumerate(conv.turns):
                cumulative += turn.tokens
                points.append({"turn": i + 1, "cumulative_tokens": cumulative})
            trends.append({
                "conversation_id": len(trends),
                "total_turns": conv.length,
                "total_tokens": conv.total_tokens,
                "trend": points,
            })
        return trends

    def reset(self):
        self._conversations = []


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def detect_key_info(response: str, key_info: Dict[str, str]) -> Dict[str, str]:
    """
    从模型回复中检测关键信息是否正确。
    简单字符串匹配版。

    返回：{key: "正确值或空字符串"}
    """
    result = {}
    for key, expected_value in key_info.items():
        if expected_value in response:
            result[key] = expected_value
        else:
            result[key] = ""
    return result
