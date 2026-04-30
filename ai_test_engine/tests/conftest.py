"""conftest for ai_test_engine/tests — 添加项目根到 sys.path"""
import sys
import os

# 将项目根目录（ai_test_engine/）添加到 sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
