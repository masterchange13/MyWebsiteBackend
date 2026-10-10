# MyWebsiteBackend

系统监控支持自动识别树莓派、Windows 和 Linux，安装、平台设置及故障排查见 [系统监控部署说明](SYSTEM_MONITOR.md)。

Video 支持服务器 USB 摄像头及树莓派 CSI 摄像头，设备选择、依赖与代理配置见 [摄像头部署说明](VIDEO_CAMERA.md)。

Video 已拆为独立 Django app `video`，无需数据库迁移。音乐音频接口支持字节范围请求，拖动进度时返回指定位置的数据；前端音乐页和底部播放器共用可拖动的进度条。运行 `python manage.py test video music config.tests` 可验证摄像头及音频范围响应。
> 本项目作为MyWebsite项目的后端，原项目使用java spring框架开发，但是现在本人打算转行python开发，所以现在使用python的django框架进行重构

本项目涉及到ws协议，所以需要使用daphne来启动项目
```
daphne -b 0.0.0.0 -p 8084 MyWebsiteBackend.asgi:application
```
