"""
门限校验与局域网网段单元测试
Unit Tests for Threshold Validation & LAN Intranet Configuration
"""

import os
import pytest
from src.common.config import get_lan_internal, DEFAULT_LAN_INTERNAL, _parse_simple_toml
from src.common.http import safe_write_file, DataValidationError
from src.address_list_rsc.main import generate_rsc_content, MIN_MAIN_ISP_COUNT

def test_lan_internal_default():
    """验证局域网保留网段默认包含 RFC 1918 标准私网段与 CGNAT 段"""
    lan = get_lan_internal()
    assert isinstance(lan, list)
    assert "10.0.0.0/8" in lan
    assert "172.16.0.0/12" in lan
    assert "192.168.0.0/16" in lan
    assert "100.64.0.0/10" in lan

def test_parse_simple_toml_array():
    """验证轻量 TOML 解析器对数组的支持"""
    content = """
    [network]
    lan_internal = ["10.0.0.0/8", "192.168.0.0/16"]
    """
    res = _parse_simple_toml(content)
    assert "network" in res
    assert res["network"]["lan_internal"] == ["10.0.0.0/8", "192.168.0.0/16"]

def test_safe_write_file(tmp_path):
    """验证原子安全写入机制"""
    target = tmp_path / "test_out.rsc"
    content = "test routeros content"
    safe_write_file(str(target), content)
    assert target.exists()
    assert target.read_text(encoding="UTF-8") == content
    assert not (tmp_path / "test_out.rsc.tmp").exists()

def test_main_rsc_threshold_guard():
    """验证当运营商抓取条目低于安全阈值时触发熔断"""
    # 构造残缺数据（条目不足 100）
    invalid_isp_data = {
        "chinatelecom_cidr": ["1.1.1.0/24"],
        "unicom_cnc_cidr": [],
        "cmcc_cidr": ["2.2.2.0/24"]
    }
    with pytest.raises(DataValidationError) as excinfo:
        generate_rsc_content(invalid_isp_data)
    assert "低于安全门限" in str(excinfo.value) or "低于安全阈值" in str(excinfo.value)

def test_main_rsc_generation_success():
    """验证正常数据可以成功生成 RSC 且包含标准局域网保留网段"""
    fake_cidrs = [f"100.{i}.0.0/16" for i in range(MIN_MAIN_ISP_COUNT + 10)]
    valid_isp_data = {
        "chinatelecom_cidr": fake_cidrs,
        "unicom_cnc_cidr": fake_cidrs,
        "cmcc_cidr": fake_cidrs
    }
    rsc = generate_rsc_content(valid_isp_data)
    assert "Loading exist_line ipv4 address list" in rsc
    assert "10.0.0.0/8" in rsc
    assert "172.16.0.0/12" in rsc
    assert "192.168.0.0/16" in rsc
    assert "100.64.0.0/10" in rsc

def test_jiangsu_threshold_guard(monkeypatch, tmp_path):
    """验证江苏地址段当条目低于安全门限时触发熔断"""
    from src.address_list_rsc.jiangsu import generate_jiangsu_rsc

    # Mock parse_jiangsu_records to return only 5 records (less than 1500)
    monkeypatch.setattr(
        "src.address_list_rsc.jiangsu.parse_jiangsu_records",
        lambda buf: [[16777216, 16777471, "南京", "电信"]] * 5
    )
    # Mock ensure_qqwry_file to return a dummy file
    dummy_db = tmp_path / "dummy_qqwry.dat"
    dummy_db.write_bytes(b"dummy" * 20)
    monkeypatch.setattr(
        "src.address_list_rsc.jiangsu.ensure_qqwry_file",
        lambda path, url: str(dummy_db)
    )

    out_file = tmp_path / "region_jiangsu.rsc"
    with pytest.raises(DataValidationError) as excinfo:
        generate_jiangsu_rsc(str(out_file), qqwry_path=str(dummy_db))
    assert "低于安全门限" in str(excinfo.value)

def test_jiangsu_parsing_real_or_mock():
    """验证江苏地址段解析器数据结构与字段完整性"""
    from src.address_list_rsc.jiangsu import parse_jiangsu_records
    import os

    qqwry_path = "/tmp/qqwry.dat"
    if os.path.exists(qqwry_path) and os.path.getsize(qqwry_path) > 1024 * 1024:
        with open(qqwry_path, "rb") as f:
            buf = f.read()
        records = parse_jiangsu_records(buf)
        assert len(records) > 1500
        # 验证首条数据格式
        rec = records[0]
        assert len(rec) == 4
        assert isinstance(rec[0], int)
        assert isinstance(rec[1], int)
        assert rec[0] <= rec[1]
        assert isinstance(rec[2], str) and len(rec[2]) > 0
        assert isinstance(rec[3], str) and len(rec[3]) > 0

def test_all_regions_threshold_guard(monkeypatch, tmp_path):
    """验证全国省份地址段当总条目低于安全门限时触发熔断"""
    from src.address_list_rsc.regions import generate_all_regions

    # Mock parse_all_provincial_records to return sparse data
    monkeypatch.setattr(
        "src.address_list_rsc.regions.parse_all_provincial_records",
        lambda buf: {"江苏": [[16777216, 16777471, "南京", "电信"]]}
    )
    dummy_db = tmp_path / "dummy_qqwry.dat"
    dummy_db.write_bytes(b"dummy" * 20)
    monkeypatch.setattr(
        "src.address_list_rsc.regions.ensure_qqwry_file",
        lambda path, url: str(dummy_db)
    )

    out_dir = tmp_path / "output"
    with pytest.raises(DataValidationError) as excinfo:
        generate_all_regions(str(out_dir), qqwry_path=str(dummy_db))
    assert "低于安全门限" in str(excinfo.value)


