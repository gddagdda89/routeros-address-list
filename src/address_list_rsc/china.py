"""
中国 IP 地址段生成器
China CIDR RSC Generator

从 https://ispip.clang.cn 获取中国全网 IP 地址列表并生成 RouterOS 地址列表导入脚本。
Retrieve the complete China IP address block list from https://ispip.clang.cn and generate a RouterOS address list script.
"""

import os
import io
import requests
from typing import Dict
from src.common.config import get_setting, resolve_path
from src.common.logging import setup_logger
from src.common.http import create_session, safe_write_file, DataValidationError

# 初始化日志器 / Initialize logger
logger = setup_logger("china_cidr")

# 默认请求地址字典 / Default request URL mapping
RULE_DICT: Dict[str, str] = {
    "all_cn_cidr": "https://ispip.clang.cn/all_cn_cidr.txt"
}

# 中国全网 IPv4 最少网段门限（正常约 8,000+ 条）
MIN_CHINA_COUNT: int = 1000

def generate_china_rsc(output_path: str) -> None:
    """
    获取中国 IP 段数据，经过安全门限校验后原子写入 RouterOS RSC 脚本文件。
    Fetch China IP block data, validate against threshold, and write atomically to RSC file.

    Args:
        output_path: RSC 文件的完整输出路径 / Complete output path for RSC file.
    """
    session = create_session()
    content_io = io.StringIO()

    for isp, url in RULE_DICT.items():
        logger.info(f"正在获取 {isp} 数据，来自: {url}")
        try:
            res = session.get(url, timeout=15)
            res.raise_for_status()
        except requests.exceptions.RequestException as req_err:
            logger.error(f"获取 {isp} 数据失败: {req_err}")
            raise DataValidationError(f"网络请求失败，无法获取 {isp}: {req_err}") from req_err

        lines = [line.strip() for line in res.text.split("\n") if len(line.strip()) > 5]
        count = len(lines)
        if count < MIN_CHINA_COUNT:
            raise DataValidationError(
                f"{isp} 抓取条目数仅为 {count}，低于安全门限 ({MIN_CHINA_COUNT})！"
                "触发熔断保护，拒绝覆盖以防 RouterOS 国内白名单被清空！"
            )

        # 写入导入前缀与日志信息 / Write import log prefix
        content_io.write(f'/log info "Loading {isp} ipv4 address list"\n')
        content_io.write(f'/ip firewall address-list remove [/ip firewall address-list find list={isp}]\n')
        content_io.write('/ip firewall address-list\n')
        for addr in lines:
            content_io.write(f':do {{ add address={addr} list={isp} }} on-error={{}}\n')
        logger.info(f"已校验并组装 {count} 条 {isp} 记录。")

    # 原子写入文件 / Atomic write
    safe_write_file(output_path, content_io.getvalue())
    logger.info(f"成功安全更新中国 IP 地址段脚本: {output_path}")

def main() -> None:
    """主程序入口 / Main entry point"""
    # 从配置中解析输出目录 / Parse output directory from config
    output_dir = resolve_path(get_setting("paths", "output_dir", "output"))
    output_file = os.path.join(output_dir, "china.rsc")

    logger.info("开始生成中国 IP 地址段脚本...")
    try:
        generate_china_rsc(output_file)
        logger.info("中国 IP 地址段脚本生成流程已全部结束。")
    except DataValidationError as val_err:
        logger.critical(f"数据校验未通过，中止生成并保留旧配置: {val_err}")
    except Exception as e:
        logger.error(f"生成中国 IP 地址段脚本失败: {e}", exc_info=True)

if __name__ == "__main__":
    main()

