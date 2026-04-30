"""conftest for ai_test_engine root — 添加项目根到 sys.path"""
import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)
