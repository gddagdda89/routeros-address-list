/log info "Loading cloudflare_ipv4 address list"
/ip firewall address-list remove [/ip firewall address-list find list=cloudflare_ipv4]
/ip firewall address-list
:do { add address=173.245.48.0/20 list=cloudflare_ipv4 } on-error={}
:do { add address=103.21.244.0/22 list=cloudflare_ipv4 } on-error={}
:do { add address=103.22.200.0/22 list=cloudflare_ipv4 } on-error={}
:do { add address=103.31.4.0/22 list=cloudflare_ipv4 } on-error={}
:do { add address=141.101.64.0/18 list=cloudflare_ipv4 } on-error={}
:do { add address=108.162.192.0/18 list=cloudflare_ipv4 } on-error={}
:do { add address=190.93.240.0/20 list=cloudflare_ipv4 } on-error={}
:do { add address=188.114.96.0/20 list=cloudflare_ipv4 } on-error={}
:do { add address=197.234.240.0/22 list=cloudflare_ipv4 } on-error={}
:do { add address=198.41.128.0/17 list=cloudflare_ipv4 } on-error={}
:do { add address=162.158.0.0/15 list=cloudflare_ipv4 } on-error={}
:do { add address=104.16.0.0/13 list=cloudflare_ipv4 } on-error={}
:do { add address=104.24.0.0/14 list=cloudflare_ipv4 } on-error={}
:do { add address=172.64.0.0/13 list=cloudflare_ipv4 } on-error={}
:do { add address=131.0.72.0/22 list=cloudflare_ipv4 } on-error={}
/log info "Loading cloudflare_ipv6 address list"
/ipv6 firewall address-list remove [/ipv6 firewall address-list find list=cloudflare_ipv6]
/ipv6 firewall address-list
:do { add address=2400:cb00::/32 list=cloudflare_ipv6 } on-error={}
:do { add address=2606:4700::/32 list=cloudflare_ipv6 } on-error={}
:do { add address=2803:f800::/32 list=cloudflare_ipv6 } on-error={}
:do { add address=2405:b500::/32 list=cloudflare_ipv6 } on-error={}
:do { add address=2405:8100::/32 list=cloudflare_ipv6 } on-error={}
:do { add address=2a06:98c0::/29 list=cloudflare_ipv6 } on-error={}
:do { add address=2c0f:f248::/32 list=cloudflare_ipv6 } on-error={}
