"""
ISP IPv4 地址列表脚本生成器
ISP IPv4 Address List Generator

从 clang.cn 获取各大主要运营商 (电信、联通、移动等) IPv4 地址列表，生成 RouterOS 地址列表导入脚本，并进行版本差异比对。
Retrieve major ISP IPv4 lists from clang.cn, generate RouterOS address list scripts, and perform differential analysis with existing versions.
"""

import os
import requests
import difflib
import io
from typing import Dict, List, Set
from src.common.config import get_setting, resolve_path, get_lan_internal
from src.common.logging import setup_logger
from src.common.http import create_session, safe_write_file, DataValidationError

# 初始化日志器 / Initialize logger
logger = setup_logger("isp_ipv4")

# 各大运营商数据源映射 / Major ISPs data sources
RULE_DICT: Dict[str, str] = {
    "chinatelecom_cidr": "https://ispip.clang.cn/chinatelecom_cidr.txt",
    "unicom_cnc_cidr": "https://ispip.clang.cn/unicom_cnc_cidr.txt",
    "cmcc_cidr": "https://ispip.clang.cn/cmcc_cidr.txt",
    "crtc_cidr": "https://ispip.clang.cn/crtc_cidr.txt",
    "gwbn_cidr": "https://ispip.clang.cn/gwbn_cidr.txt",
    "cernet_cidr": "https://ispip.clang.cn/cernet_cidr.txt",
    "hk_cidr": "https://ispip.clang.cn/hk_cidr.txt",
    "mo_cidr": "https://ispip.clang.cn/mo_cidr.txt",
    "tw_cidr": "https://ispip.clang.cn/tw_cidr.txt",
    "othernet_cidr": "https://ispip.clang.cn/othernet_cidr.txt"
}

# 三大运营商标识 / Big three ISPs key list
MAIN_ISPS: List[str] = ["chinatelecom_cidr", "unicom_cnc_cidr", "cmcc_cidr"]

# 单个核心运营商最少网段条目门限，低于此值视为抓取异常，触发熔断保护
MIN_MAIN_ISP_COUNT: int = 100


def fetch_isp_data(rule_map: Dict[str, str], session: requests.Session) -> Dict[str, List[str]]:
    """
    获取 rule_map 中所有 ISP 的 IP 地址数据。
    Retrieve IP address data for all ISPs in rule_map.

    Args:
        rule_map: ISP名称与URL映射字典 / ISP name to URL dictionary.
        session: HTTP 会话对象 / HTTP session object.

    Returns:
        将 ISP 名称映射到地址列表的字典 / Dictionary mapping ISP names to address lists.
    """
    isp_data: Dict[str, List[str]] = {}
    for isp, url in rule_map.items():
        logger.info(f"正在获取 {isp}，数据来源: {url}")
        try:
            res = session.get(url, timeout=15)
            res.raise_for_status()
            # 过滤空行并过滤格式 / Filter out empty lines
            addresses = [addr.strip() for addr in res.text.strip().split("\n") if addr.strip()]
            isp_data[isp] = addresses
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 {url} 数据时出错: {e}")
            isp_data[isp] = []
            
    return isp_data

def generate_rsc_content(isp_data: Dict[str, List[str]]) -> str:
    """
    根据获取的 IP 数据生成 RouterOS 脚本内容字符串。
    Generate RouterOS script content string according to fetched IP data.

    Args:
        isp_data: 运营商名称到 IP 列表的映射 / Mapping from ISP names to IP lists.

    Returns:
        RouterOS 脚本内容 / RouterOS script content string.
    """
    # 门限安全校验：三大运营商任一低于阈值则触发熔断保护，严禁生成残缺脚本
    for isp in MAIN_ISPS:
        addresses = isp_data.get(isp, [])
        if len(addresses) < MIN_MAIN_ISP_COUNT:
            raise DataValidationError(
                f"核心运营商 {isp} 抓取条目数为 {len(addresses)}，低于安全门限 ({MIN_MAIN_ISP_COUNT})！"
                "触发熔断保护，拒绝生成残缺脚本以防清空 RouterOS 生产地址列表！"
            )

    content_io = io.StringIO()

    # 第一部分：写入各个独立的 ISP 列表 / Part 1: Write individual ISP address lists
    for isp, addresses in isp_data.items():
        if not addresses:
            continue
        content_io.write(f'/log info "Loading {isp} ipv4 address list"\n')
        content_io.write(f'/ip firewall address-list remove [/ip firewall address-list find list={isp}]\n')
        content_io.write('/ip firewall address-list\n')
        for addr in addresses:
            content_io.write(f':do {{ add address={addr} list={isp} }} on-error={{}}\n')
        content_io.write('\n')  # 增加换行符以提高可读性

    # 第二部分：对 'exist_line' 的特殊处理 / Part 2: Special handling for 'exist_line'
    exist_line_isp = "exist_line"
    content_io.write(f'/log info "Loading {exist_line_isp} ipv4 address list"\n')
    content_io.write(f'/ip firewall address-list remove [/ip firewall address-list find list={exist_line_isp}]\n')
    content_io.write('/ip firewall address-list\n')

    # 添加三大主要运营商的地址 / Add major three ISPs addresses
    for isp in MAIN_ISPS:
        if isp in isp_data:
            for addr in isp_data[isp]:
                content_io.write(f':do {{ add address={addr} list={exist_line_isp} }} on-error={{}}\n')

    # 添加内部局域网地址（动态自配置读取） / Add local internal IP segments
    lan_internal = get_lan_internal()
    for addr in lan_internal:
        content_io.write(f':do {{ add address={addr} list={exist_line_isp} }} on-error={{}}\n')
    
    return content_io.getvalue()

def main() -> None:
    """主程序入口 / Main entry point"""
    # 从配置中解析输出路径 / Parse output path from config
    output_dir = resolve_path(get_setting("paths", "output_dir", "output"))
    rsc_out = os.path.join(output_dir, "isp.rsc")

    # 确保输出目录存在 / Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    old_content = ""

    # 步骤1: 检查并读取旧文件内容 / Step 1: Check and read old file content
    if os.path.exists(rsc_out):
        logger.info(f"发现已存在的脚本文件: {rsc_out}，准备进行差异比对。")
        try:
            with open(rsc_out, "r", encoding="UTF-8") as f:
                old_content = f.read()
        except IOError as e:
            logger.error(f"读取旧文件 {rsc_out} 失败: {e}")
            old_content = ""

    # 步骤2: 获取数据并生成新内容（带自动重试） / Step 2: Fetch data with retry
    session = create_session()
    isp_data = fetch_isp_data(RULE_DICT, session)

    try:
        new_content = generate_rsc_content(isp_data)
    except DataValidationError as val_err:
        logger.critical(f"数据校验失败，中止生成并保留旧配置: {val_err}")
        return

    # 步骤3: 使用原子写入保存新内容 / Step 3: Write new content atomically
    try:
        safe_write_file(rsc_out, new_content)
        logger.info(f"成功原子写入导入脚本文件: {rsc_out}")
    except IOError as e:
        logger.error(f"原子写入脚本文件 {rsc_out} 失败: {e}")
        return

    # 步骤4: 进行内容比对并输出差异 / Step 4: Perform diff analysis and display diff
    if old_content and old_content != new_content:
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"old_isp.rsc",
            tofile=f"new_isp.rsc",
        )
        diff_output = "".join(diff)
        if diff_output:
            logger.info("导入脚本文件内容已发生更新，差异如下:")
            print(diff_output)
    elif old_content and old_content == new_content:
        logger.info("新生成的脚本内容与旧文件一致，无变化。")

if __name__ == "__main__":
    main()
