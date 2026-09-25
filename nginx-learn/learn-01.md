下面这份 `nginx.conf` 是一个自洽完整的单文件版本，按你服务器上的 Ubuntu nginx/1.24.0 的路径写的，可以直接替换 `/etc/nginx/nginx.conf` 使用。文件里没有任何注释，讲解全部放在后面。

## 配置文件

```nginx
user www-data;
worker_processes auto;
pid /run/nginx.pid;
error_log /var/log/nginx/error.log warn;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    charset utf-8;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" "$http_user_agent"';
    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    server_tokens off;
    client_max_body_size 20m;

    gzip on;
    gzip_types text/css application/json application/javascript image/svg+xml;

    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;

        root /var/www/html;
        index index.html;

        location / {
            try_files $uri $uri/ =404;
        }

        location /api/ {
            proxy_pass http://127.0.0.1:8080/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location ~* \.(jpg|jpeg|png|gif|svg|ico|css|js)$ {
            expires 7d;
        }
    }
}
```

## 讲解：nginx.conf 的四层结构

nginx 配置是嵌套的块结构，指令只对它所在的块及更深层生效：

```text
全局块(最外层)  →  events  →  http  →  server  →  location
  进程怎么跑      连接怎么收   HTTP全局行为   站点      站内路由规则
```

### 全局块（最外层四行）

- `user www-data;` —— nginx 有两类进程：master 以 root 运行（只有它有权绑定 80 这种特权端口），worker 实际干活。这条让 worker 降权为 `www-data` 普通用户，万一 worker 被攻破，攻击者拿到的也只是低权限身份。
- `worker_processes auto;` —— worker 数量等于 CPU 核数。nginx 是事件驱动模型，不是“一个连接一个线程”，所以几个 worker 就能扛住上千并发，不需要开很多。
- `pid /run/nginx.pid;` —— master 把进程号写在这个文件，`systemctl reload/stop` 靠它找到主进程。
- `error_log ... warn;` —— 错误日志的文件和门槛。`warn` 级别能过滤掉琐碎提示，保留真正的问题（配置错误、upstream 挂了、权限拒绝都会出现在这里），排障第一入口。

### events 块

- `worker_connections 1024;` —— 每个 worker 最多同时维持 1024 个连接。全机理论上限 ≈ worker 数 × 1024。注意这是“连接”不是“用户”：一个浏览器打开页面会占好几条连接（keepalive 复用期间一直占着）。

### http 块：HTTP 层的全局行为

- `include /etc/nginx/mime.types;` —— 加载“扩展名 → Content-Type”对照表。没有它，nginx 给所有文件发默认类型，浏览器遇到 CSS/图片会当成下载而不是渲染，页面直接裸奔。
- `default_type application/octet-stream;` —— 表里查不到的类型一律按“二进制流”处理，触发浏览器下载，避免把未知文件硬解析成文本。
- `charset utf-8;` —— 响应头里标明 UTF-8，中文内容不乱码。
- `log_format main ...` + `access_log` —— 每个请求记一行：来源 IP、时间、请求行、状态码、响应字节数、来源页、User-Agent。以后排查“谁在刷我”“为什么 404”全靠 grep 这个文件。
- `sendfile on;` —— 静态文件直接在内核空间从磁盘拷到网络socket，跳过用户态来回搬运，省 CPU。
- `tcp_nopush on;` —— 响应头和文件开头数据合并成一个包发出，减少小包，与 sendfile 配套。
- `keepalive_timeout 65;` —— TCP 连接用完保留 65 秒供同一客户端复用。一个页面加载会发几十个请求，不复用的话每次都要重新三次握手，开销翻倍。
- `server_tokens off;` —— 响应头和错误页里不再显示 `nginx/1.24.0` 版本号。不改变安全性，但收掉一个最廉价的指纹信息。
- `client_max_body_size 20m;` —— 单个请求体（上传）上限 20M。默认只有 1M，之后你若部署后端应用，上传稍大的文件会被 nginx 用 413 直接拦掉、后端根本收不到——提前放宽到 20M。
- `gzip on;` + `gzip_types ...;` —— 对 CSS/JS/JSON/SVG 这类文本响应实时压缩，通常省 70% 以上流量。`text/html` 不用列（gzip 开了就默认压缩）；jpg/png 本身已是压缩格式，列进去反而浪费 CPU。

### server 块：一个“站点”

- `listen 80 default_server;`（及 `[::]:80` 的 IPv6 版）—— 监听 80 端口；`default_server` 表示：当一个请求的 Host 头不匹配任何 server_name 时，由这个块兜底。你目前只有一个站点，它就是唯一入口。
- `server_name _;` —— 占位符，配合上面的兜底语义，表示“不挑域名”。
- `root /var/www/html;` —— URL 到文件系统的映射基准：请求 `/img/a.png` 就是找 `/var/www/html/img/a.png`。
- `index index.html;` —— 请求的是目录时（如 `/`），优先返回目录下的这个文件。

### 三个 location：站内的路由分工

nginx 选 location 的规则一句话：**前缀匹配取最长，正则匹配优先于前缀**。这三个块各管一路：

**`location /`** —— 兜底的静态文件服务。`try_files $uri $uri/ =404` 按顺序尝试：当作文件找 → 当作目录找 → 都没有就返回 404。这是静态站的标配写法，杜绝了“路径不存在时返回目录列表或 500”的杂症。

**`location /api/`** —— 反向代理，这份配置里最有含金量的部分。命中 `/api/` 开头的请求不再找本地文件，而是转发给本机 8080 端口的后端应用。注意 `proxy_pass` 末尾那个 `/`：它会把 `/api/` 前缀剥掉再转发（`/api/users` → 后端收到 `/users`）。四条 `proxy_set_header` 解决同一个问题——后端看到的请求来自 nginx 而不是真实用户，所以要把原始信息补传过去：`Host` 传原始域名，`X-Real-IP` 和 `X-Forwarded-For` 传真实客户端 IP，`X-Forwarded-Proto` 传原始协议（http 还是 https）。这就是标准的“nginx 挡在前、应用躲在后”架构：静态请求 nginx 自己处理，动态请求转给应用，应用永远不直接暴露公网。

**`location ~* \.(...)$`** —— 正则匹配（`~*` 表示不区分大小写）所有图片/样式/脚本后缀的请求，`expires 7d` 告诉浏览器这批文件缓存 7 天（响应头带 `Cache-Control: max-age=604800`）。静态资源内容不变，缓存能显著减少重复下载。改了 CSS 后想强制刷新，浏览器 Ctrl+F5 绕过缓存即可。

## 部署三步

```bash
# [云服务器]
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak     # 备份原文件
nginx -t && systemctl reload nginx                     # 语法检查通过才热加载
echo '<h1>It works on my server</h1>' > /var/www/html/index.html
```

两个注意点：这份文件没有 `include sites-enabled`，Ubuntu 自带的默认站点会一并失效（本文件中的 server 取而代之），这正是单文件版的目的；`/var/www/html` 里没有 `index.html` 之前，访问首页会得到 403，先放一个再访问。如果 80 端口的安全组规则你还没加，配置再对外网也进不来——浏览器访问 `http://47.97.243.250/` 能看到你写的标题，就是全链路通了。