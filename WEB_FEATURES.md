# 网站终端与电子书部署

新增独立 Django app：`terminal` 和 `ebooks`。前端入口分别在 **Tools → 服务器终端**、**Media Hub → 电子书**；旧的菜单排序会自动补上新入口。

## 更新部署

后端使用实际运行 Daphne 的 Python 环境：

```sh
python -m pip install -r requirements.txt
python manage.py migrate
```

前端安装依赖并重新构建，将整个 `dist` 同步到服务器（包括 `pdfjs/` 和 PDF worker）：

```sh
npm ci
npm run build
```

重启后端，同步根目录 Nginx 配置并检查、重载。示例代理端口是 8084，须与实际 Daphne 端口一致。终端新增 `/terminal/ws/` 的 WebSocket 代理；上传限制设置为 55 MB，配合默认 50 MB 电子书限制。HTTPS 页面使用 WSS。

## 用户等级、摄像头与终端权限

**摄像头与终端统一由数据库 `users_user.is_advanced` 字段控制。** `1` 为高级用户，`0` 为普通用户，默认普通用户。旧的 `TERMINAL_ALLOWED_USERS` 环境变量不再用于授权。迁移 `0011` 将已有 `can_use_terminal` 字段重命名并保留值：此前有终端权限的账号将成为高级用户，也可使用摄像头。无需自动创建或按用户名默认提权。终端保留登录、CSRF、Origin、会话和一次性连接令牌校验；摄像头状态和视频流均检查高级用户权限。

Windows / Linux / 树莓派均可在后端目录、实际运行服务的 Python 环境中执行：

```sh
python manage.py migrate
python manage.py set_user_level admin advanced
```

撤销权限：

```sh
python manage.py set_user_level admin normal
```

也可以登录 Django 管理后台 `/admin/`，进入 **Users → Users**，勾选或取消对应网站用户的 **高级用户** 并保存。登录管理后台使用 Django 超级用户（可通过 `python manage.py createsuperuser` 创建），与网站自定义的 `admin` 账号是两套用户记录。个人资料页显示用户类型，但不能修改。普通网站用户不能通过注册或个人资料接口自行提权。旧命令 `set_terminal_permission` 兼容保留，但会同步变更摄像头和终端权限。

授权或撤销写入数据库后不需要重启，当前终端和摄像头流约每 5 秒检查一次登录及权限，降级或退出登录后自动结束当前连接。部署新代码时仍需重启后端。

Docker Compose 升级账号：`docker compose exec backend python manage.py set_user_level admin advanced`；降级时将 `advanced` 改为 `normal`。

| 环境变量 | 默认 | 说明 |
| --- | --- | --- |
| `TERMINAL_ENABLED` | `1` | `0` 全站禁用终端；开启时仍须用户数据库权限为真 |
| `TERMINAL_WORKDIR` | 后端项目目录 | 新会话的初始目录，必须存在 |
| `TERMINAL_SHELL` | 自动 | 可指定 Shell 可执行文件的完整路径 |
| `TERMINAL_IDLE_TIMEOUT` | `600` | 无输入超时秒数，最少 60 秒 |

Windows 优先使用 PowerShell 7、Windows PowerShell，再回退 CMD，PTY 依赖为 `pywinpty`。Linux / 树莓派使用 Bash 或 `/bin/sh`，依赖 `ptyprocess`。requirements 会自动根据平台选择。Shell 拥有后端服务运行账号的系统权限，并非隔离的命令沙箱。建议后端使用专门的普通系统账号运行。

若后端运行在 Docker 中，命令也在该容器内执行，而不是直接进入宿主机系统。

现有 Docker Compose 已补入内部 Redis 服务、终端总开关和域名环境变量的传递，并将新电子书目录挂载为 `ebooks_data` 持久卷。配置域名后执行 `docker compose up -d --build`，再按上述命令为网站账号开通权限；容器启动命令会执行数据库迁移。容器端口为 8088，Nginx 的 HTTP/WebSocket 代理应对应此端口。

支持交互输入、上下键历史、Tab、Ctrl+C、窗口尺寸变化及手机端快捷按键。新会话不持久保存 Shell 历史；离开页面、断开、超时后释放 Shell 及其子进程。每个有权限的账号同时最多一个终端；同一部署多个后端进程时使用现有 Redis 缓存协调连接。

当前页面右上角的 **断开连接** 用于结束本页会话；连接过程中可点击 **取消连接**。若提示账号已有连接，可直接点击 **关闭已有连接**，等待释放后点击 **连接终端**，无需找到原标签页。关闭操作仅作用于当前登录账号的原终端，并会结束其中运行的命令。服务异常退出留下的占用会在最后续租后 45 秒内过期，正常在线连接会自动续租。此入口需要前后端一起更新部署。

连接后可点击黑色终端区域输入；手机或终端输入焦点不可用时，可使用下方命令输入框，按 Enter 或点击 **执行**，命令发送到同一个交互式 Shell。启动消息先发送连接就绪，再发送 Shell 输出，避免丢失终端对 Shell 初始化查询的回复；服务器读写异常会显示错误并关闭连接。

## 电子书

上传、下载、删除和阅读进度均按登录用户隔离。原文件和提取正文保存在 `MEDIA_ROOT/ebooks/`；未配置 MEDIA_ROOT 时使用后端的 `media/ebooks/`。不要将此目录配置为公开静态目录，访问应经过 `/api/ebooks/<id>/file/` 登录校验。请将 `media/` 挂载到持久卷并随数据库一同备份。

支持：

- TXT：UTF-8、UTF-16、GB18030，自动识别常见章节标题；长章节拆分，适配手机阅读。
- EPUB：按 spine 顺序读取目录和正文，提取书名作者；以安全纯文本阅读，原排版、图片、脚本和交互内容不展示。不支持 DRM 加密电子书。
- PDF：本地 PDF.js 渲染、翻页、恢复上次页码。worker、CMap 与标准字体资源随 dist 部署，无需外部 CDN。
- 自动保存章节、文本滚动比例、PDF 页码、字号和阅读主题；书架搜索书名作者、下载原文件和删除图书。

`EBOOK_MAX_UPLOAD_MB` 默认 50。修改此值时同步提高 Nginx `client_max_body_size`，预留 multipart 表单开销。EPUB 解压后最多 100 MB、3000 个条目，提取正文最多 20 MB。暂不支持 MOBI/AZW 等格式。

## Navigator 排序出现 403

新访问域名 `https://l1z00505038.zicp.fun` 已加入 CSRF/CORS 配置，并支持通过环境变量扩展：

```sh
export DJANGO_PUBLIC_ORIGINS='https://你的域名,https://备用域名'
```

重启后端后刷新页面。URL 必须包含 `https://` 或 `http://`，不填写路径。HTTPS 在 Nginx 终止时，代理覆盖并发送 `Host`、`X-Forwarded-Proto`；Django 已配置读取该协议头。只应通过受控代理访问后端。前端继续发送 CSRF cookie 和 `X-CSRFToken`，并展示后端具体的 CSRF 错误。

## 验证

测试使用独立的内存 SQLite、缓存和通道层，不访问部署数据库或 Redis：

```sh
python manage.py test ebooks terminal users.test_navigator_csrf video music config.tests --settings=MyWebsiteBackend.test_settings
```

前端：`npm test` 和 `npm run build`。本地开发默认连接 8084；可通过 `VITE_API_TARGET=http://127.0.0.1:其他端口` 指定独立测试后端。
