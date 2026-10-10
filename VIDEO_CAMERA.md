# 摄像头视频部署

视频显示的是 Django **后端服务器所连接的摄像头**。浏览器所在设备不会影响摄像头的选择，不会请求浏览器摄像头权限。接口需要已登录的会话。

功能由独立 Django app `video` 提供：`camera.py` 负责采集，`views.py` 提供接口，`urls.py` 管理路由，`tests.py` 覆盖模拟测试。已注册 `video.apps.VideoConfig`，无数据库模型，不需要迁移。原有 API 路径保持兼容。

前端原先请求 `/api/video_feed`，但后端没有实现对应接口，已补齐：

- `/video/status/`：探测摄像头、等待第一帧，返回平台、采集方式、实际选择的设备及配置。
- `/video_feed/`、兼容 `/video_feed`：MJPEG 实时视频流。
- 经前端/Nginx 代理后，接口带 `/api/` 前缀。

页面先验证摄像头，再显示实时画面；设备打不开、依赖缺失、权限不足或连接中断时显示原因并支持重连。每 5 秒检查一次连接状态；该检查不会重新打开摄像头。离开页面会关闭视频连接，服务器在无观众 15 秒后释放设备。同一后端进程的多个观众共用一份画面。

未连接摄像头时显示“未检测到摄像头”或“未检测到可用摄像头”，不会一直加载。连接设备后点击“重新连接”或“重试”再次探测。

## Windows / Linux 的 USB 摄像头

在实际运行后端的环境安装：

```sh
python -m pip install -r requirements.txt
```

Windows 默认尝试设备 0–3，采集方式按 DirectShow、Media Foundation、系统默认顺序回退。允许 Python/桌面应用访问摄像头，并关闭占用设备的会议软件。

Linux 默认探测 `/dev/v4l/by-id/*` 和 `/dev/video*`，使用 V4L2，并验证可以读取第一帧后才选择设备。有些 `/dev/video*` 是编码器、元数据或处理节点，并不是可直接读取的摄像头。

Linux 检查设备与权限：

```sh
ls -l /dev/video* /dev/v4l/by-id/
v4l2-ctl --list-devices
```

运行后端的用户需要访问视频设备；必要时将该用户加入 `video` 组，并重新登录或重启对应服务。

## 树莓派排线 / CSI 摄像头

使用现代 Raspberry Pi OS 的 Picamera2 / libcamera，不将 CSI 摄像头一律当成 `/dev/video0`。自动模式在 ARM Linux 上先尝试 Picamera2，失败时再尝试 USB/V4L2。

按 [Picamera2 官方安装说明](https://github.com/raspberrypi/picamera2#installation)，安装系统包并使用可访问系统包的虚拟环境：

```sh
sudo apt update
sudo apt install python3-picamera2 python3-opencv python3-venv
rpicam-hello --list-cameras
/usr/bin/python3 -m venv --system-site-packages camera_venv
source camera_venv/bin/activate
python -m pip install -r requirements.txt
python -c "from picamera2 import Picamera2; print(Picamera2.global_camera_info())"
```

较旧系统使用 `libcamera-hello --list-cameras`。`python3-libcamera` 等组件是系统依赖，单独 `pip install picamera2` 无法保证完整安装，故没有放进 Windows/Linux 的通用 pip 清单。ARM Linux 的 requirements 会跳过 OpenCV wheel，使用上述系统 `python3-opencv`，避免与 Picamera2 使用的系统 NumPy 冲突。请确认 `import cv2` 正常。

其他 ARM Linux 的 USB 摄像头同样需要系统 `python3-opencv`，虚拟环境使用 `--system-site-packages`。项目其他依赖仍需符合实际 Python/系统版本。

## 设备与采集配置

以下环境变量由后端启动进程读取，修改后重启后端；项目不会自行加载 `.env`。

| 环境变量 | 默认值 | 可选设置 |
| --- | --- | --- |
| `VIDEO_CAMERA_BACKEND` | `auto` | `auto` / `opencv` / `picamera2` |
| `VIDEO_CAMERA_DEVICE` | `auto` | Windows 的 `0`、`1`；Linux 的 `/dev/video0` 或稳定 `/dev/v4l/by-id/...`；CSI 的 `csi:0`、`csi:1` |
| `VIDEO_CAMERA_WIDTH` | `640` | 160–1920 |
| `VIDEO_CAMERA_HEIGHT` | `480` | 120–1080 |
| `VIDEO_CAMERA_FPS` | `15` | 1–30，实际能力取决于硬件 |

树莓派排线摄像头：

```sh
export VIDEO_CAMERA_BACKEND=picamera2
export VIDEO_CAMERA_DEVICE=csi:0
daphne -b 0.0.0.0 -p 8084 MyWebsiteBackend.asgi:application
```

Linux USB 摄像头：

```sh
export VIDEO_CAMERA_BACKEND=opencv
export VIDEO_CAMERA_DEVICE=/dev/video0
daphne -b 0.0.0.0 -p 8084 MyWebsiteBackend.asgi:application
```

Windows PowerShell：

```powershell
$env:VIDEO_CAMERA_BACKEND = 'auto'
$env:VIDEO_CAMERA_DEVICE = '0'
daphne -b 0.0.0.0 -p 8084 MyWebsiteBackend.asgi:application
```

摄像头流支持 Daphne/ASGI 的异步迭代，同时兼容 WSGI 的同步迭代。摄像头是独占设备，应使用单个视频后端进程；多个独立进程/容器不能共享此进程内采集器。

## Nginx / Docker

根目录 `nginx.conf` 已为视频流关闭缓冲和缓存；部署时同步配置并重载 Nginx。后端也返回 `X-Accel-Buffering: no`。代理端口要与实际后端一致：项目示例是 8084，现有 Docker Compose 映射为 8088。

Docker 的默认镜像没有映射摄像头。USB 摄像头必须显式传入设备并允许容器用户访问，例如在 backend 服务中设置：

```yaml
devices:
  - /dev/video0:/dev/video0
environment:
  VIDEO_CAMERA_BACKEND: opencv
  VIDEO_CAMERA_DEVICE: /dev/video0
```

ARM Linux 容器还需要在镜像内安装匹配当前 Python 的 OpenCV（通用 requirements 在该平台跳过 wheel）。CSI 摄像头还依赖 Raspberry Pi OS 的 libcamera、设备和库；建议在树莓派宿主机运行后端。默认 `python:3.12-slim` 镜像不包含这些系统组件，不能仅靠映射 `/dev/video0` 使用 CSI 摄像头。

更新功能后重新部署前端 `dist`、重启后端并重载代理；无需数据库迁移。尚未连接实际树莓派验证硬件，可先通过相机枚举命令确认驱动已识别设备。

模拟测试不打开实际摄像头，可运行 `python manage.py test video` 检查设备选择、无设备错误、共享采集、断开释放和 ASGI/WSGI 视频响应。
