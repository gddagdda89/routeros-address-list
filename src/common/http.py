"""
HTTP 请求与文件原子写入安全工具模块
HTTP Request & Atomic File Operations Utility Module
"""

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from src.common.logging import setup_logger

logger = setup_logger("common_http")

class DataValidationError(Exception):
    """当上游数据源抓取条目不符合安全阈值时抛出的熔断异常"""
    pass

def create_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (500, 502, 503, 504)
) -> requests.Session:
    """
    创建具备自动重试与指数退避机制的 requests.Session。
    Create a requests.Session with automatic retry and exponential backoff.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def safe_write_file(target_path: str, content: str, encoding: str = "UTF-8") -> None:
    """
    原子写入文件：先写入同目录下的临时文件 (.tmp)，成功后再原子替换目标文件。
    避免程序中断或网络异常导致目标文件被置空或损坏。
    
    Atomic file write: writes to temporary file (.tmp) first, then atomically replaces target.
    """
    target_dir = os.path.dirname(target_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    
    tmp_path = f"{target_path}.tmp"
    try:
        with open(tmp_path, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise IOError(f"原子写入文件 {target_path} 失败: {e}") from e
