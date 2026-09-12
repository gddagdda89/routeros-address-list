"""
配置管理模块
Configuration Management Module

该模块用于加载和校验项目配置文件 config/settings.toml。
This module is used to load and validate the project configuration file config/settings.toml.
"""

import os
import sys
import logging
from typing import Any, Dict

# 获取项目根目录 / Get project root directory
# src/common/config.py -> src/common -> src -> project_root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保可以用 tomllib 加载 TOML / Ensure tomllib is available (Python 3.11+)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        # 兼容备用方案 / Fallback compatibility
        tomllib = None

class ConfigError(Exception):
    """配置相关异常 / Configuration related exceptions"""
    pass

def load_config() -> Dict[str, Any]:
    """
    加载配置文件并返回解析后的配置字典。
    Load configuration file and return parsed config dictionary.

    Returns:
        解析后的配置字典 / Parsed configuration dictionary.
    """
    config_path = os.path.join(PROJECT_ROOT, "config", "settings.toml")
    example_path = os.path.join(PROJECT_ROOT, "config", "settings.toml.example")

    if not os.path.exists(config_path):
        if os.path.exists(example_path):
            logging.warning(f"配置文件未找到: {config_path}，将自动使用示例配置: {example_path}")
            config_path = example_path
        else:
            raise ConfigError(f"配置文件及示例配置均未找到！目标路径: {config_path}")

    try:
        with open(config_path, "rb") as f:
            if tomllib:
                return tomllib.load(f)
            else:
                # 极其简易的本地 TOML 解析备用方案（防止环境缺失 tomli）
                content = f.read().decode("utf-8")
                return _parse_simple_toml(content)
    except Exception as e:
        raise ConfigError(f"解析配置文件出错: {e}") from e

# 标准私有保留网段基线 / RFC 1918 Standard Private Subnets Baseline
DEFAULT_LAN_INTERNAL: List[str] = [
    "10.0.0.0/8",          # RFC 1918 Standard Class A
    "172.16.0.0/12",       # RFC 1918 Standard Class B
    "192.168.0.0/16",      # RFC 1918 Standard Class C
    "100.64.0.0/10",       # RFC 6598 Carrier-Grade NAT
    "127.0.0.0/8",         # Loopback
]

def _parse_simple_toml(content: str) -> Dict[str, Any]:
    """
    一个极简的 TOML 行解析器，用于当缺少 tomllib/tomli 时的兼容性支持。
    """
    result: Dict[str, Any] = {}
    current_section = result
    
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            result[section_name] = {}
            current_section = result[section_name]
        elif "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                if not inner:
                    parsed_val = []
                else:
                    parsed_val = [item.strip().strip('"\'') for item in inner.split(",") if item.strip()]
                current_section[key] = parsed_val
            else:
                # 移除字符串的双引号
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                current_section[key] = val
            
    return result

# 全局配置缓存 / Global config cache
_config_cache: Dict[str, Any] = {}

def get_setting(section: str, key: str, default: Any = None) -> Any:
    """
    获取指定小节与键的配置值。
    """
    global _config_cache
    if not _config_cache:
        _config_cache = load_config()
    
    return _config_cache.get(section, {}).get(key, default)

def get_lan_internal() -> List[str]:
    """
    获取局域网内网网段列表。优先读取配置文件的 [network].lan_internal，未配置则使用现网完整默认值。
    Get LAN internal subnets list.
    """
    configured = get_setting("network", "lan_internal", None)
    if configured and isinstance(configured, list):
        return [str(x).strip() for x in configured if str(x).strip()]
    return list(DEFAULT_LAN_INTERNAL)

def resolve_path(relative_path: str) -> str:
    """
    将配置文件中的相对路径解析为基于项目根目录的绝对路径。
    """
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.normpath(os.path.join(PROJECT_ROOT, relative_path))

