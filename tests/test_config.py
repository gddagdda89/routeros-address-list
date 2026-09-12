"""
配置与路径解析单元测试
Unit Tests for Configuration & Path Resolution
"""

import os
from src.common.config import get_setting, resolve_path, PROJECT_ROOT

def test_project_root():
    """验证项目根目录获取是否正确 / Verify PROJECT_ROOT discovery"""
    assert os.path.exists(PROJECT_ROOT)
    assert os.path.isdir(PROJECT_ROOT)

def test_get_setting():
    """验证从 settings.toml 或示例配置读取参数 / Verify fetching config variables"""
    output_dir = get_setting("paths", "output_dir")
    assert output_dir is not None
    assert isinstance(output_dir, str)

    lan_internal = get_setting("network", "lan_internal")
    assert lan_internal is not None
    assert isinstance(lan_internal, list)

def test_resolve_path():
    """验证相对路径解析为绝对路径是否正确 / Verify path resolution"""
    resolved = resolve_path("output/isp.rsc")
    assert os.path.isabs(resolved)
    assert resolved.endswith(os.path.normpath("output/isp.rsc"))
