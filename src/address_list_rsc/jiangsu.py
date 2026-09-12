"""
江苏省 IPv4 地址列表脚本生成器
Jiangsu Province IPv4 Address List Generator

基于纯真 IP 数据库 (qqwry.dat) 遍历匹配江苏区域 IP 地址段，智能合并连续网段并生成 RouterOS 地址列表导入脚本。
Retrieve Jiangsu province IP segments from QQwry IP database (qqwry.dat), merge adjacent subnets, and generate a RouterOS address list import script.
"""

import os
import io
import struct
import socket
from typing import List, Tuple, Optional, Any
from src.common.config import get_setting, resolve_path
from src.common.logging import setup_logger
from src.common.http import create_session, safe_write_file, DataValidationError

# 初始化日志器 / Initialize logger
logger = setup_logger("jiangsu")

# 默认安全门限：江苏全省合并后最少网段数（正常约 2,500 条）
DEFAULT_MIN_JIANGSU_COUNT: int = 1500

# 默认纯真 IP 数据库下载地址
DEFAULT_QQWRY_DOWNLOAD_URL: str = (
    "https://github.com/metowolf/qqwry.dat/releases/latest/download/qqwry.dat"
)

# 江苏省 13 个设区市标准匹配表
JIANGSU_CITIES: List[str] = [
    "南京", "苏州", "无锡", "常州", "南通", "徐州",
    "扬州", "盐城", "镇江", "淮安", "宿迁", "泰州", "连云港"
]

# 运营商关键词匹配优先级映射表
ISP_KEYWORD_MAP: List[Tuple[str, str]] = [
    ("电信", "电信"),
    ("联通", "联通"),
    ("中移铁通", "铁通"),
    ("铁通", "铁通"),
    ("移动", "移动"),
    ("教育网", "教育网"),
    ("大学", "教育网"),
    ("学院", "教育网"),
    ("学校", "教育网"),
    ("科技网", "科技网"),
    ("广电", "广电"),
    ("鹏博士", "鹏博士"),
    ("长城", "鹏博士"),
    ("阿里", "阿里巴巴"),
]


def _read_int3(data: bytes, offset: int) -> int:
    return data[offset] + (data[offset + 1] << 8) + (data[offset + 2] << 16)


def _read_int4(data: bytes, offset: int) -> int:
    return (
        data[offset]
        + (data[offset + 1] << 8)
        + (data[offset + 2] << 16)
        + (data[offset + 3] << 24)
    )


def _extract_location_string(data: bytes, offset: int) -> Tuple[str, str]:
    """
    解析 qqwry.dat 中指定偏移量处的归属地国家/省市及运营商/地区字符串。
    Parse country and area strings at the specified offset in qqwry.dat.
    """
    mode = data[offset]
    if mode == 1:
        offset = _read_int3(data, offset + 1)
        mode = data[offset]

    if mode == 2:
        off1 = _read_int3(data, offset + 1)
        c = data[off1 : data.index(b"\x00", off1)]
        offset += 4
    else:
        c = data[offset : data.index(b"\x00", offset)]
        offset += len(c) + 1

    if data[offset] == 2:
        offset = _read_int3(data, offset + 1)
    p = data[offset : data.index(b"\x00", offset)]

    return (
        c.decode("gb18030", errors="replace"),
        p.decode("gb18030", errors="replace"),
    )


def ensure_qqwry_file(qqwry_path: str, download_url: str = DEFAULT_QQWRY_DOWNLOAD_URL) -> str:
    """
    确保 qqwry.dat 文件存在，若不存在则自动下载。
    Ensure qqwry.dat file exists; download automatically if not present.
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


def parse_jiangsu_records(data: bytes) -> List[List[Any]]:
    """
    流式解析纯真 IP 数据库字节流，提取并合并江苏区域 IP 段。
    Stream-parse qqwry bytes buffer, extract and merge Jiangsu IP records.

    Returns:
        合并后的 IP 列表，每个元素为 [ip_start_int, ip_end_int, city_name, isp_name]
    """
    idx_start = _read_int4(data, 0)
    idx_end = _read_int4(data, 4)
    total_segments = (idx_end - idx_start) // 7 + 1
    logger.info(f"开始解析纯真 IP 库，总索引段数: {total_segments:,}")

    extracted_records: List[List[Any]] = []

    for i in range(1, total_segments):
        cur = idx_start + i * 7
        off = _read_int3(data, cur + 4)
        c, p = _extract_location_string(data, off + 4)

        if "江苏" in c:
            ip_b = _read_int4(data, cur)
            ip_e = _read_int4(data, off)

            # 匹配设区市
            city = "未知"
            for ct in JIANGSU_CITIES:
                if ct in c:
                    city = ct
                    break

            # 匹配运营商
            isp = "未知"
            for keyword, mapped_name in ISP_KEYWORD_MAP:
                if keyword in p:
                    isp = mapped_name
                    break

            extracted_records.append([ip_b, ip_e, city, isp])

    logger.info(f"初筛提取江苏省内原生 IP 段: {len(extracted_records):,} 条")

    # 按起始 IP 升序排序
    extracted_records.sort(key=lambda x: x[0])

    # 相邻同城市、同运营商连续 IP 段聚合合并
    merged_records: List[List[Any]] = []
    for r in extracted_records:
        if not merged_records:
            merged_records.append(r)
        else:
            prev = merged_records[-1]
            if r[0] == prev[1] + 1 and r[2] == prev[2] and r[3] == prev[3]:
                prev[1] = r[1]
            else:
                merged_records.append(r)

    logger.info(f"连续相邻网段聚合完成，最终有效规则数: {len(merged_records):,} 条")
    return merged_records


def generate_jiangsu_rsc(output_path: str, qqwry_path: Optional[str] = None) -> None:
    """
    生成 RouterOS region_JiangSu 地址列表 RSC 文件。
    Generate RouterOS region_JiangSu address list RSC file.

    Args:
        output_path: 产物文件完整路径 / Output RSC file path.
        qqwry_path: 纯真 IP 数据库路径（可选） / QQwry database file path.
    """
    if not qqwry_path:
        configured_path = get_setting("qqwry", "qqwry_path", "/tmp/qqwry.dat")
        qqwry_path = resolve_path(configured_path)

    download_url = get_setting("qqwry", "download_url", DEFAULT_QQWRY_DOWNLOAD_URL)
    min_count = int(get_setting("qqwry", "min_count", DEFAULT_MIN_JIANGSU_COUNT))

    # 确保数据库文件就绪
    valid_db_path = ensure_qqwry_file(qqwry_path, download_url)

    # 读取数据库字节流
    with open(valid_db_path, "rb") as f:
        data_buffer = f.read()

    records = parse_jiangsu_records(data_buffer)

    # 门限熔断校验
    if len(records) < min_count:
        raise DataValidationError(
            f"江苏省 IP 段合并条目仅为 {len(records)}，低于安全门限 ({min_count})！"
            "触发熔断保护，拒绝生成残缺脚本以防 RouterOS 外部白名单被误截断！"
        )

    # 组装 RouterOS RSC 语法脚本
    content_io = io.StringIO()
    content_io.write('/log info "Loading region_JiangSu ipv4 address list"\n')
    content_io.write('/ip firewall address-list remove [/ip firewall address-list find list=region_JiangSu]\n')
    content_io.write('/ip firewall address-list\n')

    for r in records:
        b_str = socket.inet_ntoa(struct.pack(">I", r[0]))
        e_str = socket.inet_ntoa(struct.pack(">I", r[1]))
        addr = b_str if b_str == e_str else f"{b_str}-{e_str}"
        comment = f"江苏 {r[2]} {r[3]}"
        content_io.write(f':do {{ add address={addr} list=region_JiangSu comment="{comment}" }} on-error={{}}\n')

    safe_write_file(output_path, content_io.getvalue())
    logger.info(f"成功安全更新江苏省 IP 地址列表脚本: {output_path} (共 {len(records)} 条规则)")


def main() -> None:
    """主程序入口 / Main entry point"""
    output_dir = resolve_path(get_setting("paths", "output_dir", "output"))
    output_file = os.path.join(output_dir, "region_jiangsu.rsc")

    logger.info("开始生成江苏省 IP 地址段脚本...")
    try:
        generate_jiangsu_rsc(output_file)
        logger.info("江苏省 IP 地址段脚本生成流程已全部结束。")
    except DataValidationError as val_err:
        logger.critical(f"数据校验未通过，中止生成并保留旧配置: {val_err}")
    except Exception as e:
        logger.error(f"生成江苏省 IP 地址段脚本失败: {e}", exc_info=True)


if __name__ == "__main__":
    main()
