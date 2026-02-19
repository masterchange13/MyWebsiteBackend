# 开发记录（2026-02-19）

## 问题与修复

- 多用户数据未隔离
  - 现象：Navigator、ToDoList、Document、Music 未关联用户，服务层查询/删除跨用户混用
  - 处理：为上述模型新增 user 外键（允许为空），并在服务层按 session/username 过滤与授权删除
    - 模型变更示例：[navigator_model.py](file:///d:/vscode/code/python/MyWebsiteBackend/users/models/navigator_model.py)、[to_do_list_model.py](file:///d:/vscode/code/python/MyWebsiteBackend/to_do_list/models/to_do_list_model.py)、[document_model.py](file:///d:/vscode/code/python/MyWebsiteBackend/document/models/document_model.py)、[music_model.py](file:///d:/vscode/code/python/MyWebsiteBackend/music/models/music_model.py)
    - 服务层示例：[navigator_service.py](file:///d:/vscode/code/python/MyWebsiteBackend/users/services/navigator_service.py)、[to_do_list_service.py](file:///d:/vscode/code/python/MyWebsiteBackend/to_do_list/services/to_do_list_service.py)
- 旧数据批量归属
  - 新增接口 /users/assignAdminOwner/，将 user 为 NULL 的记录批量归属到指定用户（默认 admin）
  - 位置：[admin_owner_service.py](file:///d:/vscode/code/python/MyWebsiteBackend/users/services/admin_owner_service.py)
- 返回结构不统一
  - 统一所有 JsonResponse 为 { code, message, data }，错误也包含 data 空对象
  - 位置示例：[user_service.py](file:///d:/vscode/code/python/MyWebsiteBackend/users/services/user_service.py)、[navigator_service.py](file:///d:/vscode/code/python/MyWebsiteBackend/users/services/navigator_service.py)、[to_do_list_service.py](file:///d:/vscode/code/python/MyWebsiteBackend/to_do_list/services/to_do_list_service.py)
- 注册功能缺失
  - 前端 request.post('/users/register/')；后端新增注册接口与路由，校验用户名/邮箱唯一
  - 位置：[users/urls.py](file:///d:/vscode/code/python/MyWebsiteBackend/users/urls.py)、[users/views.py](file:///d:/vscode/code/python/MyWebsiteBackend/users/views.py)、[user_service.py:register](file:///d:/vscode/code/python/MyWebsiteBackend/users/services/user_service.py)
- Chat 功能与字段对齐
  - HTTP：/chat/getUsers、/chat/getHistory（参数 from/to；返回 sendUsername/receiveUsername/data）
  - WebSocket：/chat/ws；消息入参 data/sendUsername/receiveUsername；下发同样字段；持久化 ChatMessage
  - 位置：[chat_service.py](file:///d:/vscode/code/python/MyWebsiteBackend/chat/services/chat_service.py)、[chat_message_model.py](file:///d:/vscode/code/python/MyWebsiteBackend/chat/models/chat_message_model.py)、[consumers.py](file:///d:/vscode/code/python/MyWebsiteBackend/chat/consumers.py)、[routing.py](file:///d:/vscode/code/python/MyWebsiteBackend/chat/routing.py)
- WebSocket 握手失败（runserver）
  - 原因：runserver 是 WSGI，不处理 WebSocket；需使用 ASGI（Daphne/Uvicorn）
  - 解决：安装 channels/daphne，配置 ASGI 与 Channels，使用 daphne 启动
  - 配置位置：[settings.py](file:///d:/vscode/code/python/MyWebsiteBackend/MyWebsiteBackend/settings.py)、[asgi.py](file:///d:/vscode/code/python/MyWebsiteBackend/MyWebsiteBackend/asgi.py)
- Daphne 启动异常（Apps aren't loaded yet）
  - 原因：在 Django 初始化前导入 chat.routing，App 注册未完成
  - 解决：在 asgi.py 中先 get_asgi_application，再 import chat.routing，再构建 URLRouter
  - 修复位置：[asgi.py](file:///d:/vscode/code/python/MyWebsiteBackend/MyWebsiteBackend/asgi.py)
- 异步消费者中 ORM 操作
  - 原因：在 AsyncWebsocketConsumer 中直接使用同步 ORM 可能阻塞或报错
  - 处理：通过 asgiref.sync.sync_to_async 包裹 get_or_create、filter、create
  - 位置：[consumers.py](file:///d:/vscode/code/python/MyWebsiteBackend/chat/consumers.py)

## 知识点与实践

- 多用户数据隔离
  - 每个核心模型关联 User 外键；服务层查询/修改/删除均按当前用户过滤，防止跨用户操作
  - 旧数据迁移可先允许 NULL，再提供批量归属接口
- 接口返回规范
  - 统一结构 { code, message, data }；错误响应也包含 data 字段，便于前端稳定解析
- WebSocket 与 Django
  - WebSocket 需 ASGI 服务器；Django runserver（WSGI）不支持
  - Channels 提供路由与通道层；开发可用 InMemoryChannelLayer，生产建议 RedisChannelLayer
- ASGI 初始化顺序
  - 设置 DJANGO_SETTINGS_MODULE → get_asgi_application → import chat.routing → ProtocolTypeRouter
  - 导入顺序错误会导致 ImproperlyConfigured 或 AppRegistryNotReady
- 异步消费者中的数据库操作
  - 在 AsyncWebsocketConsumer 中使用 sync_to_async 包裹同步 ORM，避免阻塞/错误
- 参数与字段对齐
  - 与前端约定字段命名：HTTP 历史使用 from/to；消息字段使用 sendUsername/receiveUsername/data
  - 服务端兼容旧入参，渐进式调整前端

## 启动与测试说明

- 依赖安装：`pip install channels daphne`
- 迁移数据库：`python manage.py makemigrations && python manage.py migrate`
- 启动 ASGI（开发）：`daphne -b 0.0.0.0 -p 8083 MyWebsiteBackend.asgi:application`
- 前端开发（Vite 5173）：WebSocket 使用 `ws://localhost:8083/chat/ws?username=...`
- 若使用 HTTPS 或反向代理，改用 `wss://` 并在 Nginx 配置 Upgrade/Connection 头

## 后续建议

- 密码加密存储（如 bcrypt），同步更新登录校验
- 权限与所有权校验进一步完善（防越权删除/查询）
- Channels 在生产环境改用 Redis 通道层，支持多进程与水平扩展
- 为模型增加必要的唯一约束与索引（如每用户下资源名唯一）
