"""
RouterOS 全量地址列表一键构建器
RouterOS Full Address Lists Unified Builder

统一按序执行三大运营商 IPv4/IPv6、中国全网、Cloudflare 以及全国 34 省份地址列表构建流程。
Sequentially orchestrate and generate ISP IPv4/IPv6, China CIDR, Cloudflare, and all 34 provincial address lists.
"""

import time
import sys
from src.common.logging import setup_logger
from src.address_list_rsc.isp import main as build_isp
from src.address_list_rsc.ispv6 import main as build_ispv6
from src.address_list_rsc.china import main as build_china
from src.address_list_rsc.cloudflare import main as build_cloudflare
from src.address_list_rsc.regions import main as build_regions

logger = setup_logger("build_all")


def main() -> None:
    """按序执行所有规则生成器 / Execute all generators in sequence"""
    print("\n" + "=" * 65)
    print("  🚀 开始执行 RouterOS 全量地址列表自动化构建")
    print("=" * 65)

    tasks = [
        ("三大运营商 IPv4 列表 (output/isp.rsc)", build_isp),
        ("三大运营商 IPv6 列表 (output/ispv6.rsc)", build_ispv6),
        ("中国全网 IPv4 汇总列表 (output/china.rsc)", build_china),
        ("Cloudflare 官方 IP 列表 (output/cloudflare.rsc)", build_cloudflare),
        ("全国 34 省份/直辖市专属列表 (output/regions/*.rsc)", build_regions),
    ]

    total_start = time.time()
    success_count = 0

    for i, (name, task_func) in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] 正在生成: {name} ...")
        t0 = time.time()
        try:
            task_func()
            elapsed = time.time() - t0
            print(f"  -> ✅ 成功完成，耗时: {elapsed:.2f} 秒")
            success_count += 1
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  -> ❌ 构建失败: {e} (耗时: {elapsed:.2f} 秒)")
            logger.error(f"Task {name} failed: {e}", exc_info=True)
            sys.exit(1)

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 65)
    print(f"  🎉 全部规则脚本构建完成！成功: {success_count}/{len(tasks)}，总耗时: {total_elapsed:.2f} 秒")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
