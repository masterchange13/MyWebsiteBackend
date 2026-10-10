# 系统监控部署

系统监控读取的是 **Django 后端所在的服务器**。浏览器运行在手机、Windows 或 Linux 上均不影响选择。打开 `/systemMonitor` 后，页面会显示服务器名称、平台、架构及监控分区。

## 安装与启动

在实际启动后端的 Python 环境中运行：

```sh
python -m pip install -r requirements.txt
python -c "import psutil; print(psutil.__version__)"
daphne -b 0.0.0.0 -p 8084 MyWebsiteBackend.asgi:application
```

更新后需要重新构建、部署前端，并重启后端。已有部署继续使用自己的进程管理工具。Windows 也使用 Daphne，不使用仅支持 Unix 的 Gunicorn。

默认 `SYSTEM_MONITOR_PLATFORM=auto`，无需手动配置：

| 后端平台 | 自动监控配置 |
| --- | --- |
| 树莓派 Linux | 读取设备树型号，采集 CPU、内存、根分区、网络和运行时间，优先读取 CPU 热区温度 |
| 普通 Linux | 采集 CPU、内存、根分区、网络和运行时间，读取 CPU 传感器或 CPU 热区 |
| Windows | 采集 CPU、内存、系统盘、网络和运行时间；未提供的温度和 Unix 负载指标显示说明 |

## 可选设置

设置通过后端进程的环境变量传入，修改后重启后端。项目不会自动读取 `.env` 文件；使用 Docker Compose 时可在 `environment` 中填写。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `SYSTEM_MONITOR_PLATFORM` | `auto` | 可选 `auto`、`windows`、`linux`、`raspberrypi`；不匹配实际系统的设置会回退到自动识别 |
| `SYSTEM_MONITOR_DISK_PATH` | 空 | 自动选择系统分区；也可指定已有分区，如 `D:\` 或 `/mnt/data` |

Linux / 树莓派示例：

```sh
export SYSTEM_MONITOR_PLATFORM=auto
export SYSTEM_MONITOR_DISK_PATH=/
daphne -b 0.0.0.0 -p 8084 MyWebsiteBackend.asgi:application
```

Windows PowerShell 示例：

```powershell
$env:SYSTEM_MONITOR_PLATFORM = 'auto'
$env:SYSTEM_MONITOR_DISK_PATH = 'C:\'
daphne -b 0.0.0.0 -p 8084 MyWebsiteBackend.asgi:application
```

树莓派的设备树在容器内不可见时，可设置 `SYSTEM_MONITOR_PLATFORM=raspberrypi`。温度读取仍需要相关 `/sys/class/thermal` 文件可见且可读。Docker 内默认显示的是容器可见的磁盘、网络与系统信息；这些值不保证等同于完整宿主机指标，Windows 上的 Linux 容器会识别为 Linux。

## 故障排查

- 页面之前始终“加载中”：前端未关闭加载状态，已修复；成功后显示数据，失败显示原因。
- 提示未登录：监控接口要求有效登录会话，先登录。
- 提示缺少 `psutil`：在运行后端的同一 Python 环境安装依赖，并重启服务；Docker 部署需重建镜像。
- HTTP 404 / 502 或超时：检查后端版本、服务端口和 `/api/system-status/` 的代理；当前前端开发代理和根目录 Nginx 示例均指向 8084，Docker Compose 映射的是 8088，应按实际部署保持一致。
- 某个指标显示 `--`：硬件、权限、容器或系统不支持该指标；页面会保留其余数据并显示采集异常。

### Windows 安装时出现 SSL EOF

若 PyPI 和镜像均报 `SSLEOFError`，`from versions: none` 可能只是无法获取版本列表。本项目 Windows 开发机已确认：经本机代理安装失败，直连安装 `psutil==7.1.3` 成功。这种情况可以仅在安装期间绕过代理，保留 HTTPS 证书校验：

```powershell
$monitorPreviousNoProxy = $env:NO_PROXY
try {
    $env:NO_PROXY = '*'
    python -m pip install -r requirements.txt --index-url https://pypi.org/simple
} finally {
    $env:NO_PROXY = $monitorPreviousNoProxy
}
```

此方式要求网络允许直连 PyPI，不会修改 Windows 系统代理。若网络必须经过代理，则应修复代理的 HTTPS 连接，而不是更改依赖版本。

Windows 温度说明：[psutil 官方传感器文档](https://psutil.io/api/#psutil.sensors_temperatures)仅列出 Linux / FreeBSD 温度采集支持。本项目不会把磁盘或主板温度当作 CPU 温度。
