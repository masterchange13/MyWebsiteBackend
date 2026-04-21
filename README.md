# MyWebsiteBackend
> 本项目作为MyWebsite项目的后端，原项目使用java spring框架开发，但是现在本人打算转行python开发，所以现在使用python的django框架进行重构

本项目涉及到ws协议，所以需要使用daphne来启动项目
```
daphne -b 0.0.0.0 -p 8084 MyWebsiteBackend.asgi:application
```
