"""
全国各省份 IPv4 地址列表生成器
China Provincial IPv4 Address List Generator

基于纯真 IP 数据库 (qqwry.dat) 单次高效扫描全网 IP 段，分类提取全国 34 个省、自治区、直辖市及特别行政区的 IP 地址，
智能聚合连续网段并输出标准 RouterOS .rsc 地址列表导入脚本。
Stream-parse QQwry IP database (qqwry.dat) in a single pass, extract all 34 Chinese provinces/regions,
merge adjacent continuous subnets, and generate standard RouterOS .rsc address list scripts.
"""

import os
import io
import shutil
import struct
import socket
from typing import List, Tuple, Dict, Optional, Any
from src.common.config import get_setting, resolve_path
from src.common.logging import setup_logger
from src.common.http import safe_write_file, DataValidationError
from src.common.qqwry import ensure_qqwry_file, read_int3, read_int4, extract_location_string, DEFAULT_QQWRY_DOWNLOAD_URL

# 初始化日志器 / Initialize logger
logger = setup_logger("regions")

# 全国 34 个省级行政区元数据表：(中文名, 拼音 slug, RouterOS 驼峰命名)
PROVINCES: List[Tuple[str, str, str]] = [
    ("北京", "beijing", "BeiJing"),
    ("天津", "tianjin", "TianJin"),
    ("河北", "hebei", "HeBei"),
    ("山西", "shanxi", "ShanXi"),
    ("内蒙古", "neimenggu", "NeiMengGu"),
    ("辽宁", "liaoning", "LiaoNing"),
    ("吉林", "jilin", "JiLin"),
    ("黑龙江", "heilongjiang", "HeiLongJiang"),
    ("上海", "shanghai", "ShangHai"),
    ("江苏", "jiangsu", "JiangSu"),
    ("浙江", "zhejiang", "ZheJiang"),
    ("安徽", "anhui", "AnHui"),
    ("福建", "fujian", "FuJian"),
    ("江西", "jiangxi", "JiangXi"),
    ("山东", "shandong", "ShanDong"),
    ("河南", "henan", "HeNan"),
    ("湖北", "hubei", "HuBei"),
    ("湖南", "hunan", "HuNan"),
    ("广东", "guangdong", "GuangDong"),
    ("广西", "guangxi", "GuangXi"),
    ("海南", "hainan", "HaiNan"),
    ("重庆", "chongqing", "ChongQing"),
    ("四川", "sichuan", "SiChuan"),
    ("贵州", "guizhou", "GuiZhou"),
    ("云南", "yunnan", "YunNan"),
    ("西藏", "xizang", "XiZang"),
    ("陕西", "shaanxi", "ShaanXi"),
    ("甘肃", "gansu", "GanSu"),
    ("青海", "qinghai", "QingHai"),
    ("宁夏", "ningxia", "NingXia"),
    ("新疆", "xinjiang", "XinJiang"),
    ("香港", "hongkong", "HongKong"),
    ("澳门", "macau", "Macau"),
    ("台湾", "taiwan", "TaiWan"),
]

# 运营商关键词映射
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

# 全国省份合并后总规则门限（正常约 70,000+ 条）
MIN_TOTAL_REGIONS_COUNT: int = 30000


def parse_all_provincial_records(data: bytes) -> Dict[str, List[List[Any]]]:
    """
    单次流式扫描纯真 IP 数据库，提取并聚合全国 34 个省份的 IP 网段。
    Single-pass parse of QQwry buffer, extracting and merging records for all 34 provinces.

    Returns:
        字典：省份中文名 -> 聚合后的 IP 列表 [[ip_b, ip_e, city, isp], ...]
    """
    idx_start = read_int4(data, 0)
    idx_end = read_int4(data, 4)
    total_segments = (idx_end - idx_start) // 7 + 1
    logger.info(f"开始全国省份单次扫描，总索引段数: {total_segments:,}")

    # 初始化各省份收集池
    raw_pools: Dict[str, List[List[Any]]] = {name: [] for name, _, _ in PROVINCES}

    for i in range(1, total_segments):
        cur = idx_start + i * 7
        off = read_int3(data, cur + 4)
        c, p = extract_location_string(data, off + 4)

        for name, _, _ in PROVINCES:
            if name in c:
                ip_b = read_int4(data, cur)
                ip_e = read_int4(data, off)

                # 提取城市信息（剔除中国与省名）
                parts = c.replace("–", "-").split("-")
                city = "未知"
                for part in parts:
                    clean = part.strip()
                    if clean and clean not in ["中国", name]:
                        city = clean
                        break

                # 提取运营商
                isp = "未知"
                for keyword, mapped_name in ISP_KEYWORD_MAP:
                    if keyword in p:
                        isp = mapped_name
                        break

                raw_pools[name].append([ip_b, ip_e, city, isp])
                break

    # 针对各省分别排序并执行连续相同 (city, isp) 网段聚合
    merged_results: Dict[str, List[List[Any]]] = {}
    total_merged = 0

    for name, records in raw_pools.items():
        records.sort(key=lambda x: x[0])
        merged: List[List[Any]] = []
        for r in records:
            if not merged:
                merged.append(r)
            else:
                prev = merged[-1]
                if r[0] == prev[1] + 1 and r[2] == prev[2] and r[3] == prev[3]:
                    prev[1] = r[1]
                else:
                    merged.append(r)
        merged_results[name] = merged
        total_merged += len(merged)

    logger.info(f"全国 34 省份聚合完毕，总有效规则数: {total_merged:,} 条")
    return merged_results


def generate_all_regions(output_dir: str, qqwry_path: Optional[str] = None) -> None:
    """
    生成全国 34 个省份的 RouterOS 地址列表脚本文件。
    Generate standard RouterOS address list scripts for all 34 provinces.

    Args:
        output_dir: 基础输出目录（通常为 output/）
        qqwry_path: 纯真 IP 数据库路径（可选）
    """
    if not qqwry_path:
        configured_path = get_setting("qqwry", "qqwry_path", "/tmp/qqwry.dat")
        qqwry_path = resolve_path(configured_path)

    download_url = get_setting("qqwry", "download_url", DEFAULT_QQWRY_DOWNLOAD_URL)

    valid_db_path = ensure_qqwry_file(qqwry_path, download_url)
    with open(valid_db_path, "rb") as f:
        data_buffer = f.read()

    prov_results = parse_all_provincial_records(data_buffer)

    # 门限安全校验
    total_count = sum(len(records) for records in prov_results.values())
    if total_count < MIN_TOTAL_REGIONS_COUNT:
        raise DataValidationError(
            f"全国省份地址段合并总数仅为 {total_count}，低于安全门限 ({MIN_TOTAL_REGIONS_COUNT})！"
            "触发熔断保护，拒绝覆盖产物以防白名单被意外清空！"
        )

    # 确保 output/regions/ 目录存在
    regions_dir = os.path.join(output_dir, "regions")
    os.makedirs(regions_dir, exist_ok=True)

    for name, slug, ros_name in PROVINCES:
        records = prov_results.get(name, [])
        list_name = f"region_{ros_name}"
        out_file = os.path.join(regions_dir, f"region_{slug}.rsc")

        content_io = io.StringIO()
        content_io.write(f'/log info "Loading {list_name} ipv4 address list"\n')
        content_io.write(f'/ip firewall address-list remove [/ip firewall address-list find list={list_name}]\n')
        content_io.write('/ip firewall address-list\n')

        for r in records:
            b_str = socket.inet_ntoa(struct.pack(">I", r[0]))
            e_str = socket.inet_ntoa(struct.pack(">I", r[1]))
            addr = b_str if b_str == e_str else f"{b_str}-{e_str}"
            comment = f"{name} {r[2]} {r[3]}"
            content_io.write(f':do {{ add address={addr} list={list_name} comment="{comment}" }} on-error={{}}\n')

        safe_write_file(out_file, content_io.getvalue())

    logger.info(f"全国 34 个省份地址列表已成功写入至: {regions_dir}/")


def main() -> None:
    """主程序入口 / Main entry point"""
    output_dir = resolve_path(get_setting("paths", "output_dir", "output"))

    logger.info("开始执行全国 34 省份 IP 地址列表批量生成...")
    try:
        generate_all_regions(output_dir)
        logger.info("全国各省份 IP 地址列表生成流程已全部结束。")
    except DataValidationError as val_err:
        logger.critical(f"数据校验未通过，中止生成并保留旧配置: {val_err}")
    except Exception as e:
        logger.error(f"生成全国省份 IP 地址段脚本失败: {e}", exc_info=True)


if __name__ == "__main__":
    main()
