"""
Cloudflare IP 地址段生成器
Cloudflare IP Blocks RSC Generator

从 Cloudflare 官方获取最新的 IPv4 和 IPv6 地址列表并生成 RouterOS 地址列表导入脚本。
Retrieve the latest IPv4 and IPv6 block lists from Cloudflare official and generate a RouterOS address list script.
"""

import os
import io
import requests
from typing import Dict
from src.common.config import get_setting, resolve_path
from src.common.logging import setup_logger
from src.common.http import create_session, safe_write_file, DataValidationError

# 初始化日志器 / Initialize logger
logger = setup_logger("cloudflare")

# 默认官方数据源 / Default Cloudflare data sources
RULE_DICT: Dict[str, str] = {
    "cloudflare_ipv4": "https://www.cloudflare.com/ips-v4",
    "cloudflare_ipv6": "https://www.cloudflare.com/ips-v6"
}

MIN_CF_COUNTS = {
    "cloudflare_ipv4": 5,
    "cloudflare_ipv6": 3
}

def generate_cloudflare_rsc(output_path: str) -> None:
    """
    获取 Cloudflare IP 列表，校验完整性后原子写入 RouterOS RSC 脚本文件。
    Fetch Cloudflare IP list, validate thresholds, and write atomically to RSC file.

    Args:
        output_path: RSC 文件的完整输出路径 / Complete output path for RSC file.
    """
    session = create_session()
    content_io = io.StringIO()

    for isp, url in RULE_DICT.items():
        logger.info(f"正在获取 {isp}，来自: {url}")
        try:
            res = session.get(url, timeout=15)
            res.raise_for_status()
        except requests.exceptions.RequestException as req_err:
            logger.error(f"获取 {isp} 数据失败: {req_err}")
            raise DataValidationError(f"网络请求失败，无法获取 {isp}: {req_err}") from req_err

        lines = [line.strip() for line in res.text.split("\n") if len(line.strip()) > 5]
        min_expected = MIN_CF_COUNTS.get(isp, 1)
        if len(lines) < min_expected:
            raise DataValidationError(
                f"{isp} 获取条目数仅为 {len(lines)}，低于安全门限 ({min_expected})！"
                "触发熔断保护，拒绝覆盖以防 RouterOS Cloudflare 规则失效！"
            )

        # 区分 IPv4 和 IPv6 处理 / Distinguish between IPv4 and IPv6
        if "ipv4" in isp:
            content_io.write(f'/log info "Loading {isp} address list"\n')
            content_io.write(f'/ip firewall address-list remove [/ip firewall address-list find list={isp}]\n')
            content_io.write('/ip firewall address-list\n')
            for line in lines:
                content_io.write(f':do {{ add address={line} list={isp} }} on-error={{}}\n')
            logger.info(f"成功将 {len(lines)} 条 IPv4 记录组装完成。")
        elif "ipv6" in isp:
            content_io.write(f'/log info "Loading {isp} address list"\n')
            content_io.write(f'/ipv6 firewall address-list remove [/ipv6 firewall address-list find list={isp}]\n')
            content_io.write('/ipv6 firewall address-list\n')
            for line in lines:
                content_io.write(f':do {{ add address={line} list={isp} }} on-error={{}}\n')
            logger.info(f"成功将 {len(lines)} 条 IPv6 记录组装完成。")

    # 原子写入文件
    safe_write_file(output_path, content_io.getvalue())
    logger.info(f"成功安全生成 Cloudflare 脚本文件: {output_path}")

def main() -> None:
    """主程序入口 / Main entry point"""
    # 从配置中解析输出目录 / Parse output directory from config
    output_dir = resolve_path(get_setting("paths", "output_dir", "output"))
    output_file = os.path.join(output_dir, "cloudflare.rsc")

    logger.info("开始生成 Cloudflare IP 地址段脚本...")
    try:
        generate_cloudflare_rsc(output_file)
        logger.info("Cloudflare IP 地址段脚本生成流程已结束。")
    except DataValidationError as val_err:
        logger.critical(f"数据校验未通过，中止生成并保留旧配置: {val_err}")
    except Exception as e:
        logger.error(f"生成 Cloudflare 脚本失败: {e}", exc_info=True)

if __name__ == "__main__":
    main()

