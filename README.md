# RouterOS Address List Generator

> **项目说明**：本项目基础逻辑最初于 2023 年由人工编写并在生产环境中稳定运行，后续由 AI 辅助完成模块化重构、异常门限熔断保护、全国 34 省份扩展及 README 编写。 AI真的太好用了！！！！！

每周自动抓取并生成中国主流运营商、全国 IP 段、Cloudflare 以及**全国 34 个省份/直辖市/特区独立划分**的 RouterOS 地址列表 (`.rsc`) 脚本。

仓库已配置 GitHub Actions / Gitea Actions，每周日凌晨自动更新 `output/` 及 `output/regions/` 目录下的产物。你可以直接在 RouterOS 中拉取使用，也可以 Fork 本仓库配置你自己的内网网段。

---

## 产物列表与导入方式

生成的 `.rsc` 文件存放在 [`output/`](./output) 目录中，支持通过 RouterOS 终端直接下载并导入：

### 1. 通用核心地址列表

| 脚本文件 | 包含的 Address List | 说明 |
|---|---|---|
| `output/isp.rsc` | `chinatelecom_cidr`<br>`unicom_cnc_cidr`<br>`cmcc_cidr`<br>`crtc_cidr`<br>`exist_line` | 三大运营商 + 铁通 IPv4 网段。<br>`exist_line` 汇总了上述运营商及常用内网保留段。 |
| `output/china.rsc` | `all_cn_cidr` | 中国全网 IPv4 网段汇总。 |
| `output/ispv6.rsc` | `chinatelecom_ipv6`<br>`unicom_cnc_ipv6`<br>`cmcc_ipv6`<br>`all_cn_ipv6` | 三大运营商 IPv6 及中国全网 IPv6 汇总。 |
| `output/cloudflare.rsc` | `cloudflare_ipv4`<br>`cloudflare_ipv6` | Cloudflare 官方公布的全球 Anycast IP 网段。 |

### 2. 全国各省份/直辖市/特区专属列表 (34 省全覆盖)

每个省份脚本均存放于 [`output/regions/`](./output/regions)，基于纯真 IP 库提取并聚合相邻网段，规则自带设区市与运营商注释（如 `;;; 江苏 南京 电信`、`;;; 山东 济南 联通`），专用于家庭宽带/企业出口的外部暴露服务端口安全放行与白名单精细化访问控制：

<details>
<summary><b>点击展开：查看全国 34 省份文件对照表</b></summary>

| 省份/地区 | 脚本文件路径 | 对应 RouterOS Address List 名称 |
|---|---|---|
| **北京** | `output/regions/region_beijing.rsc` | `region_BeiJing` |
| **上海** | `output/regions/region_shanghai.rsc` | `region_ShangHai` |
| **广东** | `output/regions/region_guangdong.rsc` | `region_GuangDong` |
| **江苏** | `output/regions/region_jiangsu.rsc` | `region_JiangSu` |
| **浙江** | `output/regions/region_zhejiang.rsc` | `region_ZheJiang` |
| **山东** | `output/regions/region_shandong.rsc` | `region_ShanDong` |
| **天津** | `output/regions/region_tianjin.rsc` | `region_TianJin` |
| **重庆** | `output/regions/region_chongqing.rsc` | `region_ChongQing` |
| **河北** | `output/regions/region_hebei.rsc` | `region_HeBei` |
| **山西** | `output/regions/region_shanxi.rsc` | `region_ShanXi` |
| **河南** | `output/regions/region_henan.rsc` | `region_HeNan` |
| **湖北** | `output/regions/region_hubei.rsc` | `region_HuBei` |
| **湖南** | `output/regions/region_hunan.rsc` | `region_HuNan` |
| **安徽** | `output/regions/region_anhui.rsc` | `region_AnHui` |
| **福建** | `output/regions/region_fujian.rsc` | `region_FuJian` |
| **江西** | `output/regions/region_jiangxi.rsc` | `region_JiangXi` |
| **四川** | `output/regions/region_sichuan.rsc` | `region_SiChuan` |
| **陕西** | `output/regions/region_shaanxi.rsc` | `region_ShaanXi` |
| **辽宁** | `output/regions/region_liaoning.rsc` | `region_LiaoNing` |
| **吉林** | `output/regions/region_jilin.rsc` | `region_JiLin` |
| **黑龙江** | `output/regions/region_heilongjiang.rsc` | `region_HeiLongJiang` |
| **内蒙古** | `output/regions/region_neimenggu.rsc` | `region_NeiMengGu` |
| **广西** | `output/regions/region_guangxi.rsc` | `region_GuangXi` |
| **海南** | `output/regions/region_hainan.rsc` | `region_HaiNan` |
| **贵州** | `output/regions/region_guizhou.rsc` | `region_GuiZhou` |
| **云南** | `output/regions/region_yunnan.rsc` | `region_YunNan` |
| **西藏** | `output/regions/region_xizang.rsc` | `region_XiZang` |
| **甘肃** | `output/regions/region_gansu.rsc` | `region_GanSu` |
| **青海** | `output/regions/region_qinghai.rsc` | `region_QingHai` |
| **宁夏** | `output/regions/region_ningxia.rsc` | `region_NingXia` |
| **新疆** | `output/regions/region_xinjiang.rsc` | `region_XinJiang` |
| **香港** | `output/regions/region_hongkong.rsc` | `region_HongKong` |
| **澳门** | `output/regions/region_macau.rsc` | `region_Macau` |
| **台湾** | `output/regions/region_taiwan.rsc` | `region_TaiWan` |

</details>

---

## RouterOS 一键下载与导入命令

可以直接使用本项目官方预生成的规则脚本（若 Fork 本仓库请将链接中的 `gddagdda89` 替换为你自己的 GitHub 用户名）：

```routeros
# 示例 1：下载并导入三大运营商 IPv4 列表 (isp.rsc)
/tool fetch url="https://raw.githubusercontent.com/gddagdda89/routeros-address-list/main/output/isp.rsc" dst-path=isp.rsc
/import file-name=isp.rsc

# 示例 2：下载并导入特定省份（如江苏）白名单
/tool fetch url="https://raw.githubusercontent.com/gddagdda89/routeros-address-list/main/output/regions/region_jiangsu.rsc" dst-path=region_jiangsu.rsc
/import file-name=region_jiangsu.rsc

# 示例 3：下载并导入特定省份（如山东）白名单
/tool fetch url="https://raw.githubusercontent.com/gddagdda89/routeros-address-list/main/output/regions/region_shandong.rsc" dst-path=region_shandong.rsc
/import file-name=region_shandong.rsc
```

### 💡 国内宽带加速下载技巧
如果你的 RouterOS 直连 GitHub 出现超时或连接被重置，可使用国内加速镜像代理拉取（在 URL 前拼接代理前缀）：

```routeros
/tool fetch url="https://ghfast.top/https://raw.githubusercontent.com/gddagdda89/routeros-address-list/main/output/regions/region_guangdong.rsc" dst-path=region_guangdong.rsc
/import file-name=region_guangdong.rsc
```

### 🚀 进阶技巧：零断流原子热替换（避免白名单真空期）
默认脚本会先执行 `remove` 清空列表再逐行 `add`。如果不想在导入的 2~3 秒内产生白名单断流真空期，可在 RouterOS 终端使用两行命令完成原子切换：

```routeros
# 1. 导入新规则并统一标记为 _stage 临时表
/import file-name=region_jiangsu.rsc
# 2. 一键批量热替换
/ip firewall address-list remove [find where list="region_JiangSu"]
/ip firewall address-list set [find where list="region_JiangSu_stage"] list="region_JiangSu"
```

---

## 核心应用场景与 RouterOS 防火墙配置示例

获取到这些地址列表后，可以在 RouterOS 中实现多项经典实用的网络与安全策略：

### 1. 公网暴露端口的“本省访问白名单”防护（强烈推荐）
**场景**：家庭或机房宽带开启了外网映射端口（如 Web 控制台、文件同步、智能家居服务等）。若直接向全网暴露，每天会遭到成千上万次来自全球黑客扫描器与字典爆破。  
**方案**：通过绑定省份地址列表（以江苏 `region_JiangSu` 为例），在 Forward 链实施“非本省 IP 直接丢弃”，拦截 99% 以上的外部未知威胁：

```routeros
# 方式 A：非本省来源直接阻断（最简干脆）
# 示例端口：8080 (Web), 8443 (HTTPS), 5001 (管理面板)
/ip firewall filter
add chain=forward action=drop protocol=tcp dst-port=8080,8443,5001 \
    in-interface-list=WAN src-address-list=!region_JiangSu \
    comment="DROP: 非本省公网 IP 禁止访问内部暴露服务端口"

# 方式 B：严格白名单放行 + 默认阻断
add chain=forward action=accept protocol=tcp dst-port=8080,8443,5001 \
    in-interface-list=WAN src-address-list=region_JiangSu \
    comment="ALLOW: 仅放行省内 IP 访问服务映射"
add chain=forward action=drop protocol=tcp dst-port=8080,8443,5001 \
    in-interface-list=WAN comment="DROP: 拦截其余未经授权的外部来源"
```

---

### 2. 多宽带多运营商策略路由分流（Multi-WAN Policy Routing）
**场景**：路由器接有多条宽带（如电信 + 联通 + 移动），希望实现“访问电信走电信出口、访问联通走联通出口”，规避跨网劣化与延迟。  
**方案**：利用 `isp.rsc` 中的运营商网段对出站流量打上路由标记（Routing Mark）：

```routeros
/ip firewall mangle
# 目标 IP 属于电信，标记走电信路由表
add chain=prerouting action=mark-routing new-routing-mark=to_telecom passthrough=yes \
    src-address-list=lan_internal dst-address-list=chinatelecom_cidr comment="Route: Telecom"

# 目标 IP 属于联通，标记走联通路由表
add chain=prerouting action=mark-routing new-routing-mark=to_unicom passthrough=yes \
    src-address-list=lan_internal dst-address-list=unicom_cnc_cidr comment="Route: Unicom"

# 目标 IP 属于移动，标记走移动路由表
add chain=prerouting action=mark-routing new-routing-mark=to_cmcc passthrough=yes \
    src-address-list=lan_internal dst-address-list=cmcc_cidr comment="Route: CMCC"
```

---

### 3. 局域网终端防 WebRTC / 海外 STUN 泄露
**场景**：局域网客户端使用透明代理等工具时，浏览器 WebRTC 或即时通讯软件的 STUN 探测会直连海外纯公网 IP，导致客户端真实公网 IP 外泄。  
**方案**：利用 `all_cn_cidr`，在 Forward 链拦截所有去往非大陆 IP 的 STUN 端口探测：

```routeros
/ip firewall filter
add chain=forward action=drop protocol=udp dst-port=3478,5349,19302-19309 \
    in-interface-list=LAN dst-address-list=!all_cn_cidr \
    comment="FWD-DROP: 拦截所有访问海外纯 IP 的 WebRTC/STUN UDP 探测"
```

---

## 防护机制

为防止上游数据源宕机或网络抓取超时导致 RouterOS 上的地址列表被清空，代码内设置了安全保护：
- **抓取门限熔断**：核心运营商单项若小于 100 条、全国段小于 1,000 条、或全省份汇总小于 30,000 条时，脚本立即报错并终止，保留原有旧文件，拒绝生成残缺脚本。
- **原子替换**：脚本先写入临时文件，全部校验通过后再替换原文件，避免写入中断产生空配置。

---

## 本地运行与自定义配置

如果你需要修改加入 `exist_line` 的内网网段（如多 VLAN、WireGuard 网段），可以复制配置模板：

```bash
cp config/settings.toml.example config/settings.toml
```

在 `config/settings.toml` 中按需添加你自己的私网段：

```toml
[network]
lan_internal = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "100.64.0.0/10"
]
```

安装依赖并执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 运行测试
pytest

# 手动生成全部列表（含全国 34 省份）
python -m src.address_list_rsc.main
python -m src.address_list_rsc.mainv6
python -m src.address_list_rsc.china
python -m src.address_list_rsc.cloudflare
python -m src.address_list_rsc.regions
```

---

## 数据来源与致谢

感谢以下项目提供公开、及时的 IP 数据源：

- [ispip.clang.cn](https://ispip.clang.cn/)（维护者 [@clangcn](https://github.com/clangcn/ispip)）：提供每日更新的中国运营商及全国 IPv4/IPv6 CIDR 地址列表。
- [metowolf/qqwry.dat](https://github.com/metowolf/qqwry.dat)：提供每周自动构建更新的纯真 IP 数据库发行版，用于全国各省份与城市网段解析。
- [Cloudflare IP Ranges](https://www.cloudflare.com/ips/)：提供官方 CDN Anycast IP 接口。

---

## 免责声明 (Disclaimer)

1. 本项目生成的 RouterOS 地址列表脚本及代码仅供个人学习、网络运维、策略路由及网络安全防御参考使用。
2. IP 归属及运营商数据来源于第三方公开开源数据源，作者不对数据的绝对准确性、时效性或因使用本脚本产生的任何直接或间接网络中断、业务故障承担责任。
3. 任何个人或组织在使用本项目产物时，均应遵守当地法律法规，严禁用于任何非法网络活动。

---

## License

本项目基于 [MIT License](LICENSE) 协议开源。你可以自由使用、修改、分发及商用。
Copyright (c) 2023-2026 gddagdda89
