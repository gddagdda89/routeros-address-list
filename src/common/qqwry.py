"""
纯真 IP 数据库解析模块
QQwry IP Database Parsing & Management Module

提供纯真 IP 数据库 (qqwry.dat) 的自动化下载、缓存校验、二进制字节流指针读取与地理位置解码。
Provides automated download, cache validation, binary stream parsing, and location string decoding for QQwry IP database.
"""

import os
from typing import Tuple
from src.common.logging import setup_logger
from src.common.http import create_session, DataValidationError

# 初始化日志器 / Initialize logger
logger = setup_logger("qqwry")

# 默认纯真 IP 数据库上游下载地址 (metowolf 自动构建发布版)
DEFAULT_QQWRY_DOWNLOAD_URL: str = (
    "https://github.com/metowolf/qqwry.dat/releases/latest/download/qqwry.dat"
)


def read_int3(data: bytes, offset: int) -> int:
    """从二进制缓冲区中读取 3 字节小端整数 / Read 3-byte little-endian integer."""
    return data[offset] + (data[offset + 1] << 8) + (data[offset + 2] << 16)


def read_int4(data: bytes, offset: int) -> int:
    """从二进制缓冲区中读取 4 字节小端整数 / Read 4-byte little-endian integer."""
    return (
        data[offset]
        + (data[offset + 1] << 8)
        + (data[offset + 2] << 16)
        + (data[offset + 3] << 24)
    )


def extract_location_string(data: bytes, offset: int) -> Tuple[str, str]:
    """
    解析 qqwry.dat 中指定偏移量处的归属地国家/省市及运营商/地区字符串。
    Parse country/region and ISP/area strings at the specified offset in qqwry.dat.

    Args:
        data: 完整 qqwry.dat 内存字节流 / Full qqwry.dat bytes buffer.
        offset: 记录数据区偏移量 / Record data area offset.

    Returns:
        (country, area) 字符串元组 / Tuple of decoded location strings.
    """
    mode = data[offset]
    if mode == 1:
        offset = read_int3(data, offset + 1)
        mode = data[offset]

    if mode == 2:
        off1 = read_int3(data, offset + 1)
        c = data[off1 : data.index(b"\x00", off1)]
        offset += 4
    else:
        c = data[offset : data.index(b"\x00", offset)]
        offset += len(c) + 1

    if data[offset] == 2:
        offset = read_int3(data, offset + 1)
    p = data[offset : data.index(b"\x00", offset)]

    return (
        c.decode("gb18030", errors="replace"),
        p.decode("gb18030", errors="replace"),
    )


def ensure_qqwry_file(qqwry_path: str, download_url: str = DEFAULT_QQWRY_DOWNLOAD_URL) -> str:
    """
    确保 qqwry.dat 文件存在，若不存在则自动从上游下载。
    Ensure qqwry.dat file exists; automatically download if not present.

    Args:
        qqwry_path: 本地目标存储路径 / Target local file path.
        download_url: 纯真数据库下载链接 / Database download URL.

    Returns:
        验证就绪的文件绝对路径 / Validated absolute file path.
    """
    if os.path.exists(qqwry_path) and os.path.getsize(qqwry_path) > 1024 * 1024:
        logger.info(f"使用本地现有的纯真 IP 数据库: {qqwry_path} ({os.path.getsize(qqwry_path) / 1024 / 1024:.1f} MB)")
        return qqwry_path

    logger.info(f"本地 IP 数据库不存在，开始从上游下载: {download_url}")
    session = create_session()
    try:
        response = session.get(download_url, stream=True, timeout=60)
        response.raise_for_status()

        os.makedirs(os.path.dirname(os.path.abspath(qqwry_path)), exist_ok=True)
        tmp_path = f"{qqwry_path}.tmp"
        with open(tmp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        os.replace(tmp_path, qqwry_path)
        logger.info(f"成功下载纯真 IP 数据库至: {qqwry_path} ({os.path.getsize(qqwry_path) / 1024 / 1024:.1f} MB)")
        return qqwry_path
    except Exception as e:
        logger.error(f"下载纯真 IP 数据库失败: {e}")
        raise DataValidationError(f"无法获取 qqwry.dat 数据库文件: {e}") from e
