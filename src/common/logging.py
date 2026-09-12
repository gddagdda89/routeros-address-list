"""
日志管理模块
Logging Management Module

该模块用于统一初始化项目的日志配置，支持按天滚动及压缩。
This module is used to uniformly initialize logging configurations, supporting daily rotating and compression.
"""

import os
import gzip
import shutil
import logging
from logging.handlers import TimedRotatingFileHandler
from src.common.config import get_setting, resolve_path

def setup_logger(name: str = "app", level: str = "INFO") -> logging.Logger:
    """
    配置并返回一个标准的 Logger 实例。
    Configure and return a standard Logger instance.

    Args:
        name: 日志器名称 / Logger name.
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR) / Log level.

    Returns:
        初始化后的 Logger / Initialized Logger.
    """
    # 从配置获取日志目录，默认为根目录下的 logs / Get log directory from config
    configured_log_dir = get_setting("paths", "log_dir", "logs")
    log_dir = resolve_path(configured_log_dir)

    # 自动创建日志目录 / Auto-create log directory if not exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"{name}.log")
    
    # 转换为标准的 logging level / Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    # 防止重复添加 Handler / Prevent duplicate handlers
    if not logger.handlers:
        # 每天轮转，保留 7 天备份 / Daily rotation, keeping 7 backups
        handler = TimedRotatingFileHandler(
            log_file, 
            when="D", 
            interval=1, 
            backupCount=7, 
            encoding="utf-8"
        )
        
        # 格式必须符合 PYTHON.md 要求: 时间 | 级别 | 模块名:行号 | 详细描述
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
        )
        handler.setFormatter(formatter)

        # 定义日志文件的压缩器 / Compress rotated log files into .gz
        def compress_old_logs(source: str, dest: str):
            try:
                with open(source, "rb") as f_in:
                    with gzip.open(dest, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(source)
            except Exception as e:
                # 备用方案：若压缩出错则不报错，仅输出错误信息到 stderr
                import sys
                print(f"压缩日志文件 {source} 到 {dest} 失败: {e}", file=sys.stderr)

        # 设置轮转压缩 / Configure rotator to compress files with .gz
        handler.rotator = lambda source, dest: compress_old_logs(source, dest + ".gz")
        
        logger.addHandler(handler)

        # 同时也输出到控制台 / Also print to console for development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
