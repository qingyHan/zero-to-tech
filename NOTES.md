# 学习笔记 · 命令与概念速查

> 配套课程的复习用笔记，按模块追加。只记"回头要查的东西"，不讲完整原理——原理回课件。
> 当前覆盖：模块 3.5 与模块 4 全部（1–3.4 的基础内容未单独成节，用到时随用随查课件）。

## 模块 3.5：Nginx 与部署

**一句话**：Nginx 是网页服务器——在 80 端口收 HTTP 请求，按配置从磁盘返回文件，也能把 `/api/` 这类动态请求反向代理给后端应用。nginx.conf 之于 Nginx ≈ index.html 之于网页：唯一入口，其他配置经 `include` 引入。

### 配置的四层嵌套（指令只对所在块及更深层生效）

```text
全局块        →  events      →  http        →  server  →  location
进程怎么跑       连接怎么收      HTTP 全局行为    站点       站内路由规则
```

- **全局块**：`user www-data`（worker 降权，被攻破也只拿到低权限）；`worker_processes auto`（worker = 核数；事件驱动模型，几个 worker 扛上千并发）；`error_log ... warn`（**排障第一入口**：配置错误、权限拒绝都在这）。
- **events**：`worker_connections 1024`（每 worker 连接上限；注意是"连接"不是"用户"，keepalive 复用期间一直占着）。
- **http 常用指令**：`include mime.types`（没有它 CSS/图片会被浏览器当下载）；`charset utf-8`；`access_log`（排查"谁在刷我/为什么 404"靠 grep 它）；`sendfile on`（内核空间直拷省 CPU）；`keepalive_timeout 65`（连接复用，省反复三次握手）；`server_tokens off`（收掉版本号指纹）；`client_max_body_size 20m`（默认 1M，不放宽后端上传文件会被 413 拦掉）；`gzip on` + `gzip_types`（文本省 70%+ 流量；jpg/png 本身已压缩，别列）。
- **server 块**：一个 server 块 = 一个网站。`listen 80 default_server`（端口 + 兜底）；`server_name _`（占位符，不挑域名）；`root`（URL → 文件系统的映射基准）；`index`（目录请求的默认入口文件）。

### 三个 location：站内路由分工（前缀匹配取最长，正则优先于前缀）

- `location /` —— `try_files $uri $uri/ =404`：当文件找 → 当目录找 → 都没有 404。静态站标配。
- `location /api/` —— **反向代理**，最有含金量：`proxy_pass http://127.0.0.1:8080/`，末尾那个 `/` 会剥掉 `/api/` 前缀（`/api/users` → 后端收到 `/users`）。四条 `proxy_set_header` 把真实信息补传给后端（`Host` 域名、`X-Real-IP`/`X-Forwarded-For` 真实 IP、`X-Forwarded-Proto` 原始协议）。架构：**nginx 挡在前，应用躲在后**，应用永不直接暴露公网。
- `location ~* \.(jpg|png|css|js)$` —— `~*` 正则不分大小写；`expires 7d` 让静态资源缓存 7 天，强刷 Ctrl+F5。

### Ubuntu 的配置组织与生效

nginx.conf 用 `include` 串起 `conf.d/` 与 `sites-enabled/`；sites-enabled 里是**指向 sites-available 的软链接**（快捷方式，方便临时停用/恢复网站）。改配置的固定节奏：

```bash
sudo nginx -t                # 语法校验，失败别 reload（常见：漏分号、路径错）
sudo systemctl reload nginx  # reload 平滑加载不断连；restart 才是全重启
```

### 部署流程（课件 3.5 的"最朴素持续部署"）

```bash
ssh ubuntu@<公网IP>                    # 服务器上一次性：装 git、ssh-keygen 加 GitHub、git clone 到 ~/zero-to-tech
sudo vim /etc/nginx/sites-enabled/default   # 把 root 改成项目目录
sudo nginx -t && sudo systemctl reload nginx
sudo chmod o+x /home/ubuntu            # www-data 要穿越家目录的最小授权（只给 x 不给 r：能穿过，不能列目录）
```

更新流程：本地改代码 → `git add/commit/push` → 服务器 `cd ~/zero-to-tech && git pull` → 刷新浏览器。服务器目录是 GitHub 的镜像，**不要在服务器上手改文件**；pull 冲突丢弃手改用 `git checkout .`。

### 单文件 nginx.conf（可整份替换 /etc/nginx/nginx.conf 的自洽版本）

```nginx
user www-data;                            # worker 进程降权运行：万一被攻破，攻击者只拿到低权限身份
worker_processes auto;                    # worker 数 = CPU 核数；事件驱动模型，几个进程就能扛上千并发
pid /run/nginx.pid;                       # master 进程号文件，systemctl reload/stop 靠它找到主进程
# 错误日志 warn 起步：过滤琐碎提示，保留真问题——排障第一入口
error_log /var/log/nginx/error.log warn;

events {
    worker_connections 1024;              # 每个 worker 的最大连接数；是"连接"不是"用户"，keepalive 复用期间一直占着
}

http {
    include /etc/nginx/mime.types;        # 扩展名 → Content-Type 对照表；没有它 CSS/图片会被浏览器当下载
    default_type application/octet-stream;# 对照表查不到的类型按二进制流处理：触发下载而非硬解析
    charset utf-8;                        # 响应头标明编码，中文内容不乱码

    # 每请求一行日志：来源 IP / 时间 / 请求行 / 状态码 / 字节数 / 来源页 / UA
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" "$http_user_agent"';
    access_log /var/log/nginx/access.log main;   # 排查"谁在刷我 / 为什么 404"靠 grep 这个文件

    sendfile on;                          # 静态文件在内核空间直接拷到网络 socket，跳过用户态，省 CPU
    tcp_nopush on;                        # 响应头和文件开头数据合并成一个包，减少小包
    keepalive_timeout 65;                 # 连接空闲保留 65 秒供复用，省反复三次握手
    server_tokens off;                    # 响应头/错误页不显示 nginx 版本号，收掉最廉价的指纹
    client_max_body_size 20m;             # 请求体上限；默认只有 1M，不放宽后端上传文件会被 413 拦掉

    gzip on;                              # 文本响应实时压缩，通常省 70%+ 流量
    # 只压文本类；html 默认就压，jpg/png 本身已是压缩格式，列进去白费 CPU
    gzip_types text/css application/json application/javascript image/svg+xml;

    server {                              # 一个 server 块 = 一个网站
        listen 80 default_server;         # 监听 80（HTTP 默认端口）；default_server = 无 server_name 匹配时的兜底
        listen [::]:80 default_server;    # 同上的 IPv6 版
        server_name _;                    # 占位符："什么域名都接"

        root /var/www/html;               # URL → 文件系统的映射基准：/img/a.png 找 /var/www/html/img/a.png
        index index.html;                 # 请求的是目录时（如 /），优先返回这个默认入口文件

        location / {                      # 前缀匹配的兜底静态服务
            try_files $uri $uri/ =404;    # 依次尝试：当文件找 → 当目录找 → 都没有就 404
        }

        location /api/ {                  # 反向代理：动态请求转给本机 8080 的后端，应用不直接暴露公网
            # 末尾的 / 会剥掉 /api/ 前缀：/api/users → 后端收到 /users
            proxy_pass http://127.0.0.1:8080/;
            proxy_set_header Host $host;                    # 把原始域名传给后端
            proxy_set_header X-Real-IP $remote_addr;        # 真实客户端 IP（否则后端只看到 nginx）
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # 代理链逐跳追加的 IP 列表
            proxy_set_header X-Forwarded-Proto $scheme;     # 原始协议 http/https，后端生成正确链接用
        }

        # ~* = 正则匹配且不分大小写，命中所有静态资源后缀
        location ~* \.(jpg|jpeg|png|gif|svg|ico|css|js)$ {
            expires 7d;                   # 让浏览器缓存 7 天（Cache-Control: max-age=604800）；强刷 Ctrl+F5
        }
    }
}
```

换用注意：这份文件**没有 `include sites-enabled`**，Ubuntu 自带默认站点会一并失效（由文件内的 server 取代）——这正是单文件版的目的。`/var/www/html` 放上 `index.html` 之前首页是 403；云服务器安全组没放行 80 端口的话，配置再对外网也进不来。

```bash
# [云服务器]
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak   # 先备份
nginx -t && systemctl reload nginx                   # 校验通过才热加载
```

## 模块 4.1：现代前端第一步——模块化

**一句话**：模块化 = 用 `export`/`import` 把"藏在 `<script>` 排列顺序里的暗依赖"变成"文件顶部的明依赖"，共享从"往 window 挂全局"变成"明文声明"。ES = ECMAScript，JS 的官方标准；ES 模块就是 JS 自带的官方模块系统（import/export 在 ES6/2015 定义，浏览器约 2017 年才原生支持；更早只有 Node.js 2009 年带的非官方 CommonJS）。

### 传统写法的两大灾难

1. **顺序坑（暗依赖）**：cards.js 用了 anime，但这条依赖只藏在 `<script>` 标签的排列顺序里，代码里没有任何声明。把两行对调 → 控制台报 `Uncaught ReferenceError: anime is not defined`。
2. **全局污染**：传统 `<script>` 靠往 window（"共享台面"）挂名字共享功能；库一多，同名后到者**静默覆盖**先到者——你拿到的"纸"不是你以为的那张。

### 改造三步（HTML/CSS 一字未改，换的只是组织方式）

1. 每个 js 文件：`(function(){...})()` 立即执行改为 `export function initXxx(){...}`，anime.js 引用换成末尾带 `+esm` 的 ES 模块版 URL，依赖改成文件顶部 `import`；
2. 新建**入口** `js/main.js`，统一 import 并调用：

```js
import { initNav } from "./nav.js";
import { initCardsAnim } from "./cards.js";
import { initScoreAnim } from "./score.js";

initNav();
initCardsAnim();
initScoreAnim();
```

3. HTML 底部四个 `<script>` 合并成一行：`<script type="module" src="js/main.js"></script>`。

依赖从此写在 import 里，浏览器自动先加载再执行——顺序不再靠手排；每个模块只在自己作用域内活动——撞名消失。

### 代价与坑

- **ES 模块必须经服务器加载**：`file://` 双击打开没有来源（origin），浏览器直接 CORS 报错（安全机制：否则任意 html 能读硬盘）。部署复用模块 3.5 的 Nginx 流程。
- anime.js v4 的高级特效（如 `scrambleText`）只存在于 ES 模块版——改造前想用只能手写 setInterval。

### 伏笔

一行 import 就能用上 `stagger`、`scrambleText`——生态的力量。但"生态怎么真正驻进项目"（npm、node_modules）是 4.2 的事。

## 模块 4.2：Vite 与 npm

**一句话**：Vite 是构建工具（取代 webpack），夹在"开发者写得舒服"和"浏览器加载得快"之间做翻译。读音 /viːt/（法语"快"，不是 "vait"）。

### 它解决的三件难受

1. 模块化后不能双击 index.html → 本地开发服务器 + **热更新**（保存即刷新）；
2. 页面请求碎文件太多 → `build` 时合并（8 个 css 合成 1 个）；
3. 浏览器缓存旧文件 → 文件名加 hash（`main-Beya6efK.css`），内容变名字变，缓存自动失效。

### 命令速查

```bash
node -v                    # 确认 Node.js（Vite 是 JS 写的命令行工具，靠 Node 跑）
npm -v                     # npm 随 Node 附带，"JS 应用商店" + 项目管家

npm init -y                # 生成 package.json（唯一作用；最小合法写法是 {}）
npm install -D vite        # -D = --save-dev，装进 devDependencies
npm install animejs        # 注意：不加 -D，装进 dependencies（运行时要用）

npm run dev                # 开发：localhost:5173，随改随看
npm run build              # 打包：产出 dist/，这是上线版本
npm run preview            # 本地预览 dist/，上线前自测
```

### Vite 装哪了、怎么运行它

- `npm install -D vite` 后发生三件事：多出 **node_modules/**（vite 及连环依赖都在这，所以大）；package.json 自动加 `"devDependencies": { "vite": "^7.0.0" }`（^ = 锁 7 大版本内）；多出 **package-lock.json**（锁死精确版本，保证别处 `npm install` 结果一致，要提交 git）。
- node_modules 里有两个 vite，别混：
  - `node_modules/vite/` —— 代码本体（库住在哪儿）；
  - `node_modules/.bin/vite` —— 可执行命令（运行开关）。
- `npm run dev` = `./node_modules/.bin/vite` 的别名。别名在 package.json 的 `scripts` 里登记（dev/build/preview 名字是自己起的）；npm 只是照本宣科的执行者，先去 `.bin` 里找命令。
- `.gitignore` 应写：`node_modules`、`dist` —— 两者都能重建，不提交。

### 本节最重要的直觉：dependencies vs devDependencies

| | dependencies | devDependencies |
| --- | --- | --- |
| 类比 | 房子的**砖** | **脚手架** |
| 例子 | animejs | Vite |
| **安装命令** | `npm install 包名`（**不加 -D**） | `npm install -D 包名`（-D = --save-dev） |
| 会上线吗 | 会（运行时要用） | 不会（帮完活就撤） |

装错位置网站不一定立刻坏，但 package.json 从此失真——分不清"运行时要不要"，上线就可能少打包或多打包。

### 脚手架选型：Oxlint 还是 ESLint（create-vite 提问）

linter = 静态检查工具，写代码时就扫出"变量未定义/声明未用/不可达代码"，不用等运行。**Oxlint**：Rust 写的新一代，极快、零配置，规则集还在追赶；**ESLint**：老牌事实标准，慢些但插件生态最全。学习阶段选 Oxlint 回车即可——它只是往项目写配置和 devDependencies，以后随时能换。

### CDN 改 npm 包

```js
// 改前：从 CDN 拉
import { animate, stagger } from "https://cdn.jsdelivr.net/npm/animejs@4/+esm";
// 改后：光秃秃的名字浏览器不认，由 Vite 翻译到 node_modules 里的真实位置
import { animate, stagger } from "animejs";
```

只 `npm install` 不改 import，等于白装。

### 常见坑

- **跨平台永远首选 `npm run dev`**。
- **源代码 ≠ 运行的代码**：改网站永远改源码再重新 build，别手动改 `dist/`（下次 build 覆盖）。
- `build` 默认只认根目录 `index.html` 一个入口，`text-lab.html` 不会被打包——留给 React（4.3）解决。
- `localhost` 不是域名，就是自己这台电脑。

## 模块 4.3：React 登场——组件的规则

**一句话**：React 是一套**管 UI 的组织规则**——本质是几个 npm 包（react、react-dom），浏览器并不认识它，全部由 Vite 编译回 HTML/CSS/JS（呼应 4.2 的"翻译官"）。框架 = 管某一摊事的一套规则；React vs Vue 是同类工具的不同方言，课程选 React 只因生态最大——**可迁移的是概念，不是框架名**。

### 核心心智模型：组织方式翻转

vanilla 按**文件类型**分家（HTML 一摊、CSS 一摊、JS 一摊）；React 按**界面单元**分家——一个组件把它的结构、样式、行为、数据收拢在一起。组件 = **能独立拎走的 UI 单元**。判断要不要拆组件：能否复用、能否让代码更清爽——不是越细越好。

### JSX 的三条规则（为什么需要它）

1. JSX 就是写在组件函数 `return` 里"长得像 HTML 的东西"，**浏览器不认识**，全靠构建工具翻译——没有 4.2 装的 Vite，JSX 根本跑不起来；
2. `class` 要写成 `className`（class 是 JS 保留字）；
3. 标签大小写有含义：**大写开头 = 组件，小写开头 = 原生 HTML 标签**。组件名小写开头会被静默当成普通标签，是新手经典坑。

### props：组件的参数

`<PageHeading title="文字实验室" />` —— 传进去的是参数。同一个 Nav 组件两页**完全复用**；同一个 PageHeading 靠不同 props 显示不同标题；改一处样式两页同时生效。这就是"复用"从复制粘贴变成传参。

### 两条接入路径：挂载 vs 嵌套

- **挂载**：`createRoot(document.getElementById("root")).render(<App />)` —— 把 React 世界挂到 HTML 的一个空 div 上。整个项目**只做一次**，这是"进入 React 世界的门"。
- **嵌套**：组件放进组件，直接写标签 `<Nav />`、`<InputCard />`。

最终骨架（背下来，排障靠它定位层）：

```text
index.html（空壳，只剩一个 <div id="root">）
  └─ src/main.jsx（入口：createRoot 挂载 + import 全部 CSS）
       └─ App.jsx（总管：用 useState 记住当前页，决定渲染哪个页面组件）
            ├─ HomePage / TextLabPage（页面组件）
            │    └─ Nav / PageHeading / AnimatedCardGrid / InputCard / ResultCard（零件组件）
```

4.2 遗留问题在这里全部闭环：两个 html 内容重复 → 组件化后**只剩一个空壳 index.html**（"build 只认 index.html"的坑自动消失）；Nav 两页重复书写 → 抽成组件复用；CSS 从 HTML `<link>` 改成入口文件 `import`。

### 初见的三个 API（本节只到"认识"）

- `useState`：记住一个会变化的值。App 里 `const [page, setPage] = useState("home")` 决定当前渲染哪个页面——但"开始分析"按钮点了没反应是**故意留的**，数据驱动界面是 4.4 的主题；
- `useEffect`：组件挂载后执行一次（本节用来跑入场动画）；
- `useRef`：拿到真实 DOM 节点交给 anime.js——React 管 UI，动画库要摸真实节点。

### 命令与接入方式

```bash
npm install react react-dom           # dependencies：运行时要用（砖）
npm install -D @vitejs/plugin-react   # devDependencies：Vite 的 React 翻译插件（脚手架）
```

React 以**插件形态**接入 Vite——`vite.config.js` 里 `plugins: [react()]`，把"翻译 JSX"这条规则装进翻译官。这解释了 4.2 那句"构建工具是地基，框架往上盖"。

### 伏笔

下一节 4.4「数据驱动界面」：让 `setPage` 真正被按钮触发、输入框接上 state——点击 → 数据变 → 界面跟着变。另一层理解：造框架的技术不难，React/Vue 真正的价值在**生态**——全世界开发者写好的组件和库。

## 模块 4.4：让数据驱动界面

**一句话**：React 把"操作页面"变成"改变数据"——你只管改值，刷界面这件事 React 替你干，"值一变界面当场跟着变"就是它最核心的引擎。本节两个动作：把 state **用起来**（受控输入框），把 state **挪到更持久的地方**（URL）。

### state 的四条特征（判断一个值该不该是 state）

1. 它是组件**自己揣着**的（外部喂进来的那是 props）；
2. 有默认值：`useState(初始值)`；
3. 显示照着它来；
4. 它可以被改——且一改，显示当场跟着变。

### 受控组件：输入框接到 state

```jsx
const [text, setText] = useState("今天的风很轻，……");
<textarea value={text} onChange={(e) => setText(e.target.value)} />
<p>已输入 {text.length} 字</p>
```

理解要点：`value={text}` 让 React **接管**输入框——显示什么由 state 说了算（不是 DOM 自己记）；`onChange` 把每次敲键写回 state；text 一变，所有引用它的地方（如字数统计）自动重刷。你全程没写一句"找到那个元素再去改它"——**改数据就是改界面**，这句话就是"数据驱动"。

### state 记在内存 vs 记在 URL

4.3 的 `page` 记在内存里：刷新被打回首页、地址栏没法分享。4.4 换成 `useRoute()`，把"在哪一页"读写到地址栏：

```jsx
const [path, setPath] = useState(window.location.pathname); // 读地址栏
function navigate(to) {
  window.history.pushState({}, "", to);  // 写进地址栏（可前进后退、可复制分享）
  setPath(to);
}
// 再用 useEffect 监听 popstate，浏览器前进/后退时界面跟着变
```

URL 天生适合当路由：刷新不丢、可整条复制、可前进后退。手搓版"够用但糙"——真实项目用现成的 react-router，4.5 的 Next.js 会用"文件夹 = 路由"把它整个替掉。

### 数据与界面分离

新增 `src/data/site.js` 内容表：组件管"**怎么显示**"，site.js 管"**显示什么**"。想做个英文版，只换内容表，组件零改动——这是数据驱动最朴素的收益。伏笔：模块 5 接后端后，内容表从网络接口实时取。

### 部署多了一步（工程化的成本）

`npm run build` 产出 `dist/`（index.html + assets/ 下带 hash 的 JS/CSS）。服务器上要先装 Node、`npm install` 再 `npm run build`，Nginx 只改一行：

```nginx
root /home/ubuntu/zero-to-tech/dist;   # 指向 build 产物
```

### 伏笔

输入的字还没有消费者——"开始分析"按兵不动，情感分数是写死的假数据，都等模块 5 的后端小模型；下一节 4.5 正式请出 Next.js（路由、预渲染与生产能力）。

## 模块 4.5：Next.js——React 之上的生产级框架

**一句话**：Next.js = React 之上再加一层。React 管**组件**（UI），Next 管"组件之外、上线必须的事"——**路由**和**把页面预渲染成真实 HTML**。二者是叠加关系，不是二选一。

### 病根诊断：React SPA 的三个症状是同一个病

SPA 把空壳 index.html + 一个大 JS 包发给浏览器，页面靠 JS 在浏览器里**现画**，于是：直接访问 `/text-lab` 报 404（服务器上没这个文件）、首屏先白屏一拍（先下空壳再下 JS 再画）、SEO 差（爬虫不执行 JS，抓到空壳）。病根同一个：**页面不是真实文件**。Next 的解法——把每页提前渲染成真实 HTML 摆在服务器上，三个问题一并解决。Next 之前这些活得自己拼：react-router 加 Nginx 回退配置治 404，预渲染要自建 Node 服务器手拼 HTML 字符串。

### 文件夹 = 路由（约定优于配置）

```text
app/layout.jsx            全站外壳（页面包裹 + 引入 CSS）
app/page.jsx              → / 这一页
app/text-lab/page.jsx     → /text-lab 这一页
```

想加 `/blog` 就建 `app/blog/page.jsx`——不用注册、不用路由表。4.4 手搓的 26 行 `useRoute.js` + `App.jsx` 的页面切换**整体消失**：Nav 换成 Next 自带的 `<Link href="...">`，监听 URL、刷新不丢、前进后退全由框架接管。路由的直觉没变——URL 管界面，仍是数据驱动；只是苦差从手搓变成框架代办。

### 服务端组件 vs 客户端组件（`"use client"` 开关）

Next 默认把组件先渲染成 HTML 再发浏览器——这类叫**服务端组件**（纯展示，画完就完事，快且 SEO 好）。组件顶部写 `"use client"` = 客户端组件，带交互/动画（用 useState、useEffect、usePathname），代价是额外多送一份 JS 让它"活"起来。

**最关键的澄清**：客户端组件**也会被预渲染成 HTML**——"use client" 不是"不预渲染"，而是"还要在浏览器里再跑一遍"。所以源代码里内容都在，SEO 照样好。本项目标了 `"use client"` 的：Nav、InputCard、ResultCard、AnimatedCardGrid（有交互/动画）；没标的：两个 View、PageHeading、各 page.jsx（纯展示）。

### 从 Vite + React 迁移改了什么

```bash
npm create next-app@latest   # 从 0 新建（会问要不要 Tailwind——工具类样式方案，AI 写前端常用）
npm run dev                  # 端口从 5173 变成 3000
npm run build && npm run start   # start 用 .next 产物起本地 Node 服务器
```

package.json 只多一个 `next` 依赖；scripts 从 vite 系换成 next 系：`dev`/`build` 名字照旧，`preview` 变成了 **`start`**——语义也变，从"本地预览静态产物"变成"起 Node 服务器跑 .next"。Vite 退场是因为构建被 Next 接管，不是过时，构建概念没白学。`next build` 的输出表里每页标 `○ (Static) prerendered as static content`，且 `.next/server/app/` 下 **index.html、text-lab.html 真实存在**——"预渲染"眼见为实。

迁移清单：删 App.jsx + useRoute.js；src/ 换成 app/（layout + 各页 page.jsx）；加 next 依赖换 scripts；Nav 改 `<Link>`；交互组件加 `"use client"`；其余组件和 site.js 几乎照搬。

### 部署提醒（和 4.4 的关键差异）

`.next` 产物**不能**像 Vite 的 dist 那样直接丢给 Nginx 当静态文件——`npm run start` 是 Next 自己的 Node 服务器在兜路由，与 Nginx 静态托管不是一回事。怎么部署是 4.6 的主题。

### 伏笔

服务端组件还能在收到请求时现场算动态内容（SSR 动态渲染）；下一节 4.6 把项目部署到云主机、Nginx 指向它。

## 模块 4.6：把 Next.js 项目发布上线

**一句话**：4.5 提醒过 `.next/` 不能直接丢给 Nginx——本节的答案是**绕开它**：加一行 `output: "export"` 走**静态导出**，build 直接产出干净的 `out/` 目录，Nginx 指过去就上线，无需任何常驻进程。

### 两条上线路线（本课选 B）

- **A：常驻 Next 服务**——服务器 7×24 跑 `npm run start`（Node 进程），能按请求现画动态页面；Vercel 等平台托管走这条。代价是养一个常驻进程，课件还引了 2025-12 服务端组件 CVSS 10.0 RCE 漏洞作为顾虑之一；
- **B：静态导出（本课采用）**——页面内容 build 时定死，动态数据靠浏览器事后请求后端 API。4.5 的结论继续成立："use client" 组件照样被预渲染进 out/。

### 三处具体改动

1. `next.config.mjs` 加一行 `output: "export"` → build 产出 **out/**（不是 .next）；
2. Nginx `root` 指向 out/，try_files 升级一档：

```nginx
location / {
    # /text-lab 这种无后缀 URL：当文件找 → 补 .html 再找 → 当目录找 → 404
    try_files $uri $uri.html $uri/ =404;
}
```

3. `.gitignore` 加 `out/` 与 `.next/`（都是构建产物，不提交）。

部署链路和 3.5/4.4 是同一条：本地 push → 服务器 `git pull` → `npm install` → `npm run build` → `sudo nginx -t` → `sudo systemctl reload nginx`。上线即验收 4.5 的三个症状全部消失：无 404（text-lab.html 真实存在于 out/）、无白屏（已预渲染）、SEO 正常（源码含完整内容）。

### 伏笔

前端线到此完结。模块 5 后端（Python 独立服务）登场：把 site.js 的硬编码和"开始分析"按钮对接真实 API，前后端解耦——明确不走 Next 全栈路线。CI/CD 自动化是后话，先把链路本身走熟。

## 模块四总结：一条改造链，一张命令表

### 知识主线：同一个双页面网站被改造了六次

| 模块 | 做了什么 | 解决了什么 | 遗留给下一棒 |
| --- | --- | --- | --- |
| 4.1 模块化 | `<script>` 手排 → `import/export` + `type="module"` | 顺序坑、全局污染 | 不能双击打开（必须走服务器） |
| 4.2 Vite | 装上构建工具 | 开发服务器 + 热更新、合并碎文件、hash 缓存 | build 只认 index.html 单入口 |
| 4.3 React | 组件化 | 页面重复、Nav 复用、多入口 → 只剩空壳 index.html | 按钮没反应（数据是死的） |
| 4.4 数据驱动 | state、受控组件、URL 路由 | 界面跟着数据变、刷新丢状态 | SPA 三症状（404/白屏/SEO） |
| 4.5 Next.js | 文件夹路由 + 预渲染 | 404、白屏、SEO 一并解决 | .next 不能静态托管 |
| 4.6 上线 | 静态导出 out/ + Nginx | 真正发布 | 动态数据等后端（模块 5） |

规律：**每一阶段解决上一阶段暴露的痛点，又暴露新的**——工程化就是这么滚起来的。

### 命令全家福（按用途）

```bash
# 环境
node -v  &&  npm -v
# 项目起步（三选一）
npm init -y                    # 纯手搭：只生成 package.json
npm create vite@latest         # Vite 脚手架（4.2/4.3 路线）
npm create next-app@latest     # Next 脚手架（4.5 路线）
# 依赖（砖不加 -D，脚手架加 -D）
npm install animejs            # dependencies：运行时要用
npm install -D vite @vitejs/plugin-react   # devDependencies：开发工具
# 日常开发 / 构建
npm run dev        # 5173（Vite）→ 3000（Next），热更新
npm run build      # 产物：dist/（Vite）→ out/（Next 静态导出）/ .next/（Next 常驻）
npm run preview / npm run start
# 上线链路（服务器）
git pull && npm install && npm run build
sudo nginx -t && sudo systemctl reload nginx
```

### 概念对照速记

- **dependencies vs devDependencies**：砖 vs 脚手架（4.2）；
- **服务端组件 vs `"use client"`**：都预渲染成 HTML，后者额外多送一份 JS 好让它"活"（4.5）；
- **state 放哪**：组件内存（4.3/4.4）→ URL（4.4）→ 后端数据库（模块 5）；
- **翻译官**：Vite 翻译 JSX/模块 → Next 接管构建并预渲染——工具在换，"源代码 ≠ 运行的代码"这条主线从 4.2 贯到 4.6。

## 模块 5.1：究竟什么是 API

**一句话**：API = 程序对外公开的固定入口——按它规定的方式发请求，就能用上它的能力，无需知道内部实现。前端跑在用户浏览器里管展示；后端常驻服务器管计算与数据；两者靠 API 对话，格式通常是 JSON。

两个直观例子（GET 取数据 / POST 提交内容）：

```bash
curl 'https://api.ipify.org?format=json'          # GET：返回 {"ip":"114.86.123.45"}
curl https://api.deepseek.com/chat/completions \  # POST：提交对话，拿回 AI 回复
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \
  -d '{"model":"deepseek-v4-pro","messages":[{"role":"user","content":"你好"}]}'
```

格式标准的意义：**调用方与提供方语言无关**。AI 产品的本质就是调大模型 API，Agent 的联网工具也都在调 API。后端语言选什么都行，课程用 Python（概念与语言无关）。

## 模块 5.2：Python 环境与 venv

- **多版本共存**：`python`/`python3` 是历史遗留（2→3 不兼容），`which python3` 查明实际用的是哪个；
- **venv 虚拟环境**：每个项目一套专属 Python + 第三方包，互不冲突。`.venv` 要**激活**才生效（Linux `source .venv/bin/activate`；Windows `.venv\Scripts\activate`；退出 `deactivate`）；conda 是全局式管理，课程推荐 venv；
- **两对对应关系**：pip ≈ 前端的 npm；requirements.txt ≈ package.json（要进 Git）。`.venv/` 不进 Git；
- **Python 语法**：缩进即语法；字典 ≈ JSON（单引号 vs 双引号）。

```bash
mkdir backend && cd backend
python3 -m venv --prompt=zero-to-tech .venv
source .venv/bin/activate
pip install requests                 # 用 Python 调 API 的第三方库
pip freeze > requirements.txt        # 固化依赖清单
```

## 模块 5.3：看懂 HTTP，手搓 API

**一句话**：HTTP 报文全是纯文本，请求与响应结构对称，唯一差别在第一行（请求行 vs 状态行）。手搓一个接口就要自己做路由、状态行、响应头、空行、序列化——这些属于 HTTP 规范的杂活，正是框架（5.4）替你打包的东西。

### HTTP 请求 = 请求行 + 请求头 + 空行 + 请求体

**请求行**（第一行，三件事）：`方法 路径 协议版本`，如 `GET /api/profile?format=json HTTP/1.1`。路径是 URL 去掉协议和域名后的部分，`?` 后面是查询参数。

**请求头**（一行一条 `名字: 值`）：

| 头 | 含义 |
| --- | --- |
| Host | 要找哪台服务器 |
| User-Agent | 我是谁（什么工具/浏览器） |
| Accept | 能接受什么格式的回应 |
| Content-Type | 提交的请求体是什么格式 |
| Content-Length | 请求体有多长 |
| Authorization | 身份凭证（如 `Bearer sk-…`） |
| Cookie | 随身带的"小纸条" |

**空行**：分界线——"头说完了，下面是体"。**漏了它调用方直接报错**。
**请求体**：真正提交的内容；GET 一般没有体。

### HTTP 响应 = 状态行 + 响应头 + 空行 + 响应体

**状态行**：`协议版本 状态码 说明`，如 `HTTP/1.1 200 OK`。状态码家族规律：**2xx 成功、4xx 请求方的锅、5xx 服务器的锅**（200 成功 / 404 没找到 / 422 字段校验不过，见 5.4）。

**响应头**：

| 头 | 含义 |
| --- | --- |
| Content-Type | 回的体是什么格式（**本节主角**） |
| Content-Length | 体有多长 |
| Server / Date | 服务器软件 / 处理时间 |
| Cache-Control | 可缓存、能存多久（呼应 4.2 的 hash 文件名） |
| Set-Cookie | 发"小纸条" |
| Location | 内容搬家了（配合 3xx 跳转） |
| Access-Control-Allow-Origin | 允许哪些来源调用（5.5 CORS 的主角） |

**响应体**：正文——API 的 JSON 就放这里。

### 请求方法：描述意图，不是数据方向

| 方法 | 意图 |
| --- | --- |
| GET | 把某样东西给我（通常不带体） |
| POST | 我提交一段内容请你处理（内容放体里） |
| PUT / PATCH / DELETE | 整个换掉 / 改一部分 / 删掉 |
| HEAD / OPTIONS | 只要头不要体（探路）/ 询问能做什么 |

curl 默认发 GET，带 `-d` 自动改发 POST。响应永远都有——GET/POST 是 HTTP 的方法，不是 API 的发明。

### Content-Type：头一变，处理方式就变

内容不变，`Content-Type` 一变对方处理方式就变：`text/html` 渲染成网页、`text/plain` 原样显示、`application/json` 按 JSON 解析。浏览器眼里"网页"和"API 数据"只是 Content-Type 不同。

### 手搓代码（http.server）

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

profile = {"heroTitle": "关于我", "heroSubtitle": "项目，创意，灵感，心得，我的作品"}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/profile":                       # 路由判断 = if/elif 判 self.path
            self.send_response(200)                           # → 状态行
            self.send_header("Content-Type", "application/json")  # → 响应头
            self.end_headers()                                # → 空行（硬要求，漏了全盘皆乱）
            body = json.dumps(profile, ensure_ascii=False)    # ensure_ascii=False：中文原样输出
            self.wfile.write(body.encode("utf-8"))            # → 响应体（网络传字节，要 encode）
        else:
            self.send_response(404)                           # else 兜底
            self.end_headers()

print("后端已启动：http://localhost:8000/api/profile")
HTTPServer(("", 8000), Handler).serve_forever()   # 守在 8000 端口永远等请求
```

代码与规范一一对应：`do_GET`→方法、`self.path`→路径、`send_response`→状态行、`send_header`→响应头、`end_headers`→空行、`wfile.write`→响应体、else→404。课堂实验：加 `/hello` 分支返回 HTML（Content-Type 改 `text/html; charset=utf-8`，改成 `text/plain` 再看效果）；`do_GET` 开头 `print(self.headers)` 与 `print(self.client_address)`——服务端天然看得见 UA、IP、语言偏好（访问统计与防刷的地基）。

### 测试工具：curl -v 与 F12 是同一份报文的两个视角

```bash
curl -v 'https://api.ipify.org?format=json'   # > 请求、< 响应、* 旁白
python3 main.py                               # 终端 1：起服务（Ctrl+C 停）
curl -v http://localhost:8000/api/profile     # 终端 2：调自己的服务
```

Chrome F12 → Network 面板看到的与 `curl -v` 是同一份报文。

### 伏笔

手搓一个接口就要写全套杂活，几十个接口"是要出人命的"。一模一样的事就有人打包复用——**框架**。下一节 FastAPI 登场。

## 模块 5.4：FastAPI 登场

**一句话**：Python 最年轻的后端框架，专为写 API 而生——5.3 手搓的杂活（路由判断、状态码、响应头、JSON 序列化、404 兜底、请求体解析校验）全部打包，我们只填"这个路径返回什么数据"。官方文档：<https://fastapi.tiangolo.com/zh/>

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/api/profile")
def get_profile():
    return profile

class AnalyzeRequest(BaseModel):
    text: str                      # 字段声明一次：解析、校验、转对象全自动

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    return {"text": req.text, "score": 0.5, "label": "偏平静", "pinyin": "（模块 6 再说）"}
```

**手搓 vs 框架的分工对照**：

| 手搓版（5.3） | FastAPI |
| --- | --- |
| if/elif 判 `self.path` | `@app.get(...)` 一行装饰器 |
| `send_response(200)` + `send_header(...)` | 自动（状态行 + JSON 响应头） |
| `json.dumps(...).encode(...)` | 返回字典自动序列化 |
| else 兜底 404 | 自动（未定义路径回 `{"detail":"Not Found"}`） |
| 手读 Content-Length、收字节、解析、校验（POST） | `req: AnalyzeRequest` 声明后全自动；字段缺失/类型不对回 **422** |

分工边界：FastAPI 负责定义接口，**uvicorn 负责运行服务器**（`HTTPServer(...).serve_forever()` 的角色）。

**运行与测试**（安装：`pip install "fastapi[standard]"`）：

```bash
uvicorn main:app --reload    # main:app = 文件:变量；--reload 改代码自动重启
fastapi dev                  # 快捷方式，默认找 main.py（上线用 fastapi run）
curl http://localhost:8000/api/profile
curl http://localhost:8000/api/analyze -H "Content-Type: application/json" \
  -d '{"text": "今天的风很轻"}'
```

**自动文档**：`http://localhost:8000/docs`（Swagger UI，可 Try it out 直接调；另有 /redoc）——类型声明一次，文档、编辑器补全、数据校验、422 报错全部白拿。

**深入掌握 FastAPI**：独立的 10 课学习课程见 [`fastapi-learn/`](./fastapi-learn)——每课一个可运行 `main.py` + 验收标准 + 中文教学注释，覆盖路由、参数与校验、响应控制、依赖注入、异常与 CORS、OAuth2+JWT 认证、异步与 CRUD、项目拆分（APIRouter/配置/lifespan）、测试（TestClient/pytest），全部经行为级测试验证（35/35 通过）。

**伏笔**：score/label/pinyin 还是写死的占位值——模块 6 换成真的（内部实现换掉，接口不变）；5.5 前后端正式握手（CORS）。

## 模块 5.5：前后端联调与 CORS

**一句话**：前后端各自能跑 ≠ 能联调——前端(3000/5173)调后端(8000)是**跨源**，浏览器会拦。关键认知：**CORS 只约束浏览器**，curl 永远不受限。排查三板斧：① Network 面板（请求发出去了吗？有没有失败的 OPTIONS？）→ ② 后端终端（收到请求、返回 200 了吗？）→ ③ Console（是不是 CORS 报错？）。

### 源与同源策略

源 = **协议 + 域名 + 端口**，任一不同即不同源——3000 和 8000 端口不同，就是跨源。最重要的认知修正：简单 GET 请求**其实已经到达后端并返回了 200**，被浏览器拦下的是"网页脚本**读取**这份未经许可的跨源响应"，不是请求本身。

机制：跨源请求自动带 `Origin: http://localhost:3000` 请求头；后端若允许，响应头返回 `Access-Control-Allow-Origin: http://localhost:3000`——两边对得上，浏览器才把响应交给 JS。

### 预检请求（OPTIONS）：先问后发

带 `Content-Type: application/json` 的 POST **不是简单请求**：浏览器先自动发 `OPTIONS /api/analyze` 询问来源/方法/头是否允许，预检通过才发真正的 POST——预检不过，POST 根本不离开浏览器。目的：防止可能产生副作用的请求在未授权时就已在后端生效。curl 不是浏览器，看不到预检也不会被拦。

### 后端放行（FastAPI 两步）

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],   # 第一步：声明允许的来源 → GET 通了
    allow_methods=["GET", "POST"],             # 第二步：POST 报 "Failed to fetch"、
)                                              # Network 里看到失败的 OPTIONS → 补方法
```

预检由 CORSMiddleware 自动应答——**不需要为 OPTIONS 写任何路由**。`Content-Type` 属默认放行的常见头，不必写 `allow_headers`；将来带 token 之类自定义头才需要列出。（fastapi-learn 第 6 课的 CORS 段就是这套配置。）

### 前端配置化：把写死的后端地址收进环境变量

Next.js 用 `.env.local`（本课是 Next 而非 Vite，没有 `import.meta.env`）：

```bash
# .env.local（不进 Git）
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

```js
const API = process.env.NEXT_PUBLIC_API_BASE_URL;
fetch(`${API}/api/analyze`, { method: "POST", ... })
```

`NEXT_PUBLIC_` 前缀 = 值可进浏览器代码 → **只能放公开配置**（如后端地址），绝不能放密钥密码。修改环境变量后必须重启开发服务器。

### 联调完整链路（验收清单）

两个终端分别起后端（`fastapi dev`，8000）和前端（`npm run dev`，3000）→ 后端 `/api/profile` 数据结构对齐前端 site.js → curl 确认接口正常 → 前端组件接 fetch → 遇 CORS 逐个放行 → GET/POST 全通。最终链路：

```text
输入文字 → 浏览器 POST → OPTIONS 预检通过 → FastAPI 校验请求体
→ Python 计算 → JSON 响应 → 前端更新界面 → 结果区自动刷新
```

### 伏笔

两笔欠账：`/api/analyze` 的拼音/情感分数还是占位假数据；分析结果用完即丢无历史。模块 6.1 用 Python 第三方库把分析变成真的，并把结果保存下来。

## 附：Git 撤销提交速查

| 命令 | 提交 | 改动去哪了 | 适用 |
| --- | --- | --- | --- |
| `git reset --soft HEAD~1` | 撤销 | 回到**暂存区** | 提交信息写错 / 想补文件再提交 |
| `git reset HEAD~1` | 撤销 | 留在**工作区**（未暂存） | 想重新挑选要提交的内容 |
| `git reset --hard HEAD~1` | 撤销 | **直接丢弃** | 彻底不要这次改动（慎用，找不回） |

`HEAD~1` = 上一次提交，`HEAD~2` = 上上次。已 push 到远程时：协作场景用 `git revert HEAD`（生成反向新提交，不动历史，最安全）；个人仓库才考虑 `reset --hard` 后 `git push --force`。
