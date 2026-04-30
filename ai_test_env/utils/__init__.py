"""Utils 模块 - AI 测试工具集

包含 Day 1-26 的各种测试工具和实用模块。
支持通过旧名称（如 api_client）或新名称（如 d1_api_client）导入。
"""

from .d1_api_client import AITestClient
from .d3_error_classifier import ErrorClassifier, ErrorCategory
from .d4_response_validator import ResponseValidator
from .d5_key_manager import KeyPoolManager, DegradeManager, KeyStatus, RotateStrategy, DegradeStep
from .d6_quality_checker import QualityChecker, CheckResult
from .d7_consistency_checker import ConsistencyChecker, ConsistencyResult, get_consistency_level
from .d8_truncation_analyzer import TruncationAnalyzer, TruncationReport, FinishReason, get_truncation_level
from .d9_llm_judge import LLMJudge, JudgeResult, BatchJudgeReport, ABCompareResult
from .d10_pipeline_assessment import AssessmentPipeline, QualityReport, compute_overall_score, compute_overall_grade, format_report_console, format_version_comparison
from .d10_schema_validator import SchemaValidator
from .d11_conversation_tester import Turn, Conversation, ContextTestResult, ConversationTester, ConversationManager, detect_key_info
from .d12_injection_detector import InjectionDetector, InjectionTestReport, AttackCaseLibrary, INJECTION_TYPES
from .d12_prompt_injection_tester import InjectionType, InjectionCase, InjectionTestResult, InjectionTestReport, AttackCaseGenerator, InjectionDetector, InjectionTester
from .d13_robustness_tester import RobustnessTestType, RobustnessCase, RobustnessResult, RobustnessReport, RobustnessCaseGenerator, RobustnessDetector, RobustnessTester
from .d14_regression_tester import CaseCategory, RegressionCase, RegressionResult, RegressionReport, ABTestResult, ABTestReport, RegressionLibrary, RegressionTester
from .d15_e2e_tester import ScenarioType, SceneTurn, Scenario, ScenarioResult, E2EReport, ScenarioLibrary, ScenarioEngine, E2ETester
from .d16_browser_checker import BrowserManager, BrowserStatus, MockBrowser, MockElement, PageCheckItem, PageCheckResult, PageCheckType, PageCheckReport, PageInspector, AIAppPageChecker
from .d17_suite_manager import TestLevel, TagCategory, TestCaseMeta, TestSuiteManager, ParametrizedCase, PytestMarkerGenerator, CompatRunner, generate_test_run_summary
from .d18_ci_config_gen import GatingStrategy, GateRule, CIConfigGenerator
from .d19_toolchain_integration import ToxConfigGenerator, CoverageChecker, CoverageResult, CodeSanityChecker, SanityIssue, ProjectHealthReporter
from .d20_data_manager import DataProfile, PromptDataFactory, ResponseDataFactory, DataMasker, DataVersionTracker, DatasetEntry
from .d22_load_tester import LoadTester, LatencyReport
from .d23_retry_engine import RetryEngine, RetryStrategy, RetryStats, retry
from .d24_circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenError
from .d25_error_system import AppError, ConfigError, APIError, RateLimitError, AuthError, ValidationError, ErrorClassifier, ErrorSeverity, ErrorAction
from .d26_token_auditor import TokenAuditor, TokenRecord, DailyReport, AnomalyType, AnomalyAlert

__all__ = [
    "AITestClient",
    "ErrorClassifier",
    "ErrorCategory",
    "ResponseValidator",
    "KeyPoolManager",
    "DegradeManager",
    "KeyStatus",
    "RotateStrategy",
    "DegradeStep",
    "QualityChecker",
    "CheckResult",
    "ConsistencyChecker",
    "ConsistencyResult",
    "get_consistency_level",
    "TruncationAnalyzer",
    "TruncationReport",
    "FinishReason",
    "get_truncation_level",
    "LLMJudge",
    "JudgeResult",
    "BatchJudgeReport",
    "ABCompareResult",
    "AssessmentPipeline",
    "QualityReport",
    "compute_overall_score",
    "compute_overall_grade",
    "format_report_console",
    "format_version_comparison",
    "SchemaValidator",
    "Turn",
    "Conversation",
    "ContextTestResult",
    "ConversationTester",
    "ConversationManager",
    "detect_key_info",
    "InjectionDetector",
    "InjectionTestReport",
    "AttackCaseLibrary",
    "INJECTION_TYPES",
    "InjectionType",
    "InjectionCase",
    "InjectionTestResult",
    "AttackCaseGenerator",
    "InjectionTester",
    "RobustnessTestType",
    "RobustnessCase",
    "RobustnessResult",
    "RobustnessReport",
    "RobustnessCaseGenerator",
    "RobustnessDetector",
    "RobustnessTester",
    "CaseCategory",
    "RegressionCase",
    "RegressionResult",
    "RegressionReport",
    "ABTestResult",
    "ABTestReport",
    "RegressionLibrary",
    "RegressionTester",
    "ScenarioType",
    "SceneTurn",
    "Scenario",
    "ScenarioResult",
    "E2EReport",
    "ScenarioLibrary",
    "ScenarioEngine",
    "E2ETester",
    "BrowserManager",
    "BrowserStatus",
    "MockBrowser",
    "MockElement",
    "PageCheckItem",
    "PageCheckResult",
    "PageCheckType",
    "PageCheckReport",
    "PageInspector",
    "AIAppPageChecker",
    "TestLevel",
    "TagCategory",
    "TestCaseMeta",
    "TestSuiteManager",
    "ParametrizedCase",
    "PytestMarkerGenerator",
    "CompatRunner",
    "generate_test_run_summary",
    "GatingStrategy",
    "GateRule",
    "CIConfigGenerator",
    "ToxConfigGenerator",
    "CoverageChecker",
    "CoverageResult",
    "CodeSanityChecker",
    "SanityIssue",
    "ProjectHealthReporter",
    "DataProfile",
    "PromptDataFactory",
    "ResponseDataFactory",
    "DataMasker",
    "DataVersionTracker",
    "DatasetEntry",
    "LoadTester",
    "LatencyReport",
    "RetryEngine",
    "RetryStrategy",
    "RetryStats",
    "retry",
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpenError",
    "AppError",
    "ConfigError",
    "APIError",
    "RateLimitError",
    "AuthError",
    "ValidationError",
    "ErrorSeverity",
    "ErrorAction",
    "TokenAuditor",
    "TokenRecord",
    "DailyReport",
    "AnomalyType",
    "AnomalyAlert",
]
