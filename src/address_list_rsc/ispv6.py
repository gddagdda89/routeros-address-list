"""
ISP IPv6 地址列表脚本生成器
ISP IPv6 Address List Generator

从 clang.cn 获取各大主要运营商 (电信、联通、移动等) IPv6 地址列表，生成 RouterOS 地址列表导入脚本，并进行版本差异比对。
Retrieve major ISP IPv6 lists from clang.cn, generate RouterOS address list scripts, and perform differential analysis with existing versions.
"""

import os
import requests
import difflib
import io
from typing import Dict, List
from src.common.config import get_setting, resolve_path
from src.common.logging import setup_logger
from src.common.http import create_session, safe_write_file, DataValidationError

# 初始化日志器 / Initialize logger
logger = setup_logger("isp_ipv6")

# 各大运营商 IPv6 数据源映射 / Major ISPs IPv6 data sources
RULE_DICT: Dict[str, str] = {
    "chinatelecom_ipv6": "https://ispip.clang.cn/chinatelecom_ipv6.txt",
    "unicom_cnc_ipv6": "https://ispip.clang.cn/unicom_cnc_ipv6.txt",
    "cmcc_ipv6": "https://ispip.clang.cn/cmcc_ipv6.txt",
    "all_cn_ipv6": "https://ispip.clang.cn/all_cn_ipv6.txt",
    "othernet_ipv6": "https://ispip.clang.cn/othernet_ipv6.txt"
}

# 核心 IPv6 规则列表，任一缺少或条目过少则熔断
CORE_V6_ISPS: List[str] = ["chinatelecom_ipv6", "unicom_cnc_ipv6", "cmcc_ipv6", "all_cn_ipv6"]
MIN_ISPV6_COUNT: int = 10

def generate_ipv6_content(rule_map: Dict[str, str], session: requests.Session) -> str:
    """
    自指定 URL 获取 IPv6 数据，经门限校验后构建成 RouterOS 导入脚本字符串。
    Fetch IPv6 data, validate thresholds, and build RouterOS import script string.

    Args:
        rule_map: 规则与 URL 映射表 / Rule name to URL mapping.
        session: HTTP 请求会话 / HTTP request session.

    Returns:
        RouterOS 导入脚本内容 / RouterOS import script content.
    """
    content_io = io.StringIO()

    for isp, url in rule_map.items():
        logger.info(f"正在获取 {isp}，数据来源: {url}")
        try:
            res = session.get(url, timeout=15)
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 {url} 数据时出错: {e}")
            if isp in CORE_V6_ISPS:
                raise DataValidationError(f"核心 IPv6 规则 {isp} 请求失败: {e}") from e
            continue

        # 处理并写入 IP 地址，过滤空行 / Process and write IP addresses, filtering out empty lines
        addresses = [addr.strip() for addr in res.text.strip().split("\n") if addr.strip()]
        if isp in CORE_V6_ISPS and len(addresses) < MIN_ISPV6_COUNT:
            raise DataValidationError(
                f"核心 IPv6 规则 {isp} 条目数仅为 {len(addresses)}，低于安全门限 ({MIN_ISPV6_COUNT})！"
                "触发熔断保护，拒绝生成残缺脚本以防清空 RouterOS IPv6 地址列表！"
            )

        # 写入 RouterOS 日志前缀和命令 / Write RouterOS log prefix and commands
        content_io.write(f'/log info "Loading {isp} ipv6 address list"\n')
        content_io.write(f'/ipv6 firewall address-list remove [/ipv6 firewall address-list find list={isp}]\n')
        content_io.write('/ipv6 firewall address-list\n')

        for addr in addresses:
            content_io.write(f':do {{ add address={addr} list={isp} }} on-error={{}}\n')
        content_io.write('\n')

    return content_io.getvalue()

def main() -> None:
    """主程序入口 / Main entry point"""
    # 从配置中解析输出路径 / Parse output path from config
    output_dir = resolve_path(get_setting("paths", "output_dir", "output"))
    rsc_out = os.path.join(output_dir, "ispv6.rsc")

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

    # 步骤2: 获取数据并生成新内容 / Step 2: Fetch data and generate new content
    session = create_session()
    try:
        new_content = generate_ipv6_content(RULE_DICT, session)
    except DataValidationError as val_err:
        logger.critical(f"IPv6 数据校验未通过，中止生成并保留旧配置: {val_err}")
        return

    # 步骤3: 将新内容原子写入文件 / Step 3: Write new content atomically
    try:
        safe_write_file(rsc_out, new_content)
        logger.info(f"成功安全生成 IPv6 导入脚本文件: {rsc_out}")
    except IOError as e:
        logger.error(f"原子写入文件 {rsc_out} 失败: {e}")
        return

    # 步骤4: 如果存在旧内容，进行比对并显示差异 / Step 4: Perform diff analysis and display diff
    if old_content and old_content != new_content:
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"old_ispv6.rsc",
            tofile=f"new_ispv6.rsc",
        )
        diff_output = "".join(diff)
        if diff_output:
            logger.info("导入脚本文件已成功更新，差异如下:")
            print(diff_output)
    elif old_content and old_content == new_content:
        logger.info("新生成的脚本内容与旧文件一致，无变化。")

if __name__ == "__main__":
    main()
