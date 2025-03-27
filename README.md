# SQL查询API

一个基于FastAPI的HTTP API，用于执行SQL查询并提供测试用的Web界面。

## 功能特性

- 提供执行SQL查询的HTTP API端点
- API密钥认证
- 支持Markdown格式的SQL查询
- 多种响应格式（JSON、Markdown表格、CSV）
- Web界面用于API文档和测试
- JSON响应格式化和复制功能
- 错误处理和详细的错误信息

## 安装配置

### 方法1：本地安装

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
创建`.env`文件并设置以下变量：
```
API_KEY=your_api_key
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=your_mysql_host
MYSQL_PORT=your_mysql_port
MYSQL_DATABASE=your_mysql_database
MYSQL_RAISE_ON_WARNINGS=True
MYSQL_AUTH_PLUGIN=mysql_native_password
MYSQL_CONNECTION_TIMEOUT=10
```

3. 运行应用：
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 方法2：Docker安装

1. 配置环境变量：
创建`.env`文件并设置与上述相同的变量。

2. 使用Docker构建和运行：
```bash
# 构建Docker镜像
docker build -t sql-query-api .

# 运行容器
docker run -d \
  --name sql-query-api \
  -p 8000:8000 \
  --env-file .env \
  sql-query-api
```

### 方法3：Docker Compose安装（推荐）

1. 配置环境变量：
创建`.env`文件并设置与上述相同的变量。

2. 使用Docker Compose运行：
```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

应用将在`http://localhost:8000`可用。

## 使用说明

### Web界面

在浏览器中打开`http://localhost:8000`访问Web界面。

### API端点

**端点:** `/query`
**方法:** POST
**请求头:**
- `X-API-Key`: 您的API密钥
- `Content-Type`: application/json

**请求体:**
```json
{
    "markdown_text": "Markdown格式的SQL查询",
    "response_format": "json"  // 可选，默认为"json"。可选值："json"、"markdown"或"csv"
}
```

**请求示例:**

1. JSON格式（默认）:
```bash
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"markdown_text": "```sql\nSELECT now() AS now;\n```", "response_format": "json"}'
```

2. Markdown表格格式:
```bash
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"markdown_text": "```sql\nSELECT now() AS now;\n```", "response_format": "markdown"}'
```

3. CSV格式:
```bash
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"markdown_text": "```sql\nSELECT now() AS now;\n```", "response_format": "csv"}'
```

**响应格式:**

响应格式取决于请求中的`response_format`参数:

1. JSON格式（默认）:
```json
{
    "code": 200,
    "message": "success",
    "data": [
        // 查询结果以JSON数组形式返回
    ]
}
```

2. Markdown表格格式:
```json
{
    "code": 200,
    "message": "success",
    "data": "| 列1 | 列2 |\n|-----|-----|\n| 值1 | 值2 |"
}
```

3. CSV格式:
```json
{
    "code": 200,
    "message": "success",
    "data": "列1,列2\n值1,值2"
}
```

**响应代码:**

| 代码 | 消息 | 描述 |
|------|------|------|
| 200 | success | 查询执行成功 |
| 400 | bad_request | 无效的请求格式或参数 |
| 401 | unauthorized | 无效或缺少API密钥 |
| 403 | forbidden | 执行查询的权限不足 |
| 404 | not_found | 请求的资源不存在 |
| 422 | validation_error | 无效的SQL查询语法 |
| 500 | internal_server_error | 查询执行期间的服务器端错误 |
| 503 | service_unavailable | 数据库连接错误或服务暂时不可用 |

每个响应包含:
- `code`: 表示请求结果的HTTP状态码
- `message`: 结果的简要描述
- `data`: 查询结果（成功时）或错误详情（失败时）

**错误响应示例:**
```json
{
    "code": 400,
    "message": "bad_request",
    "error": "无效的SQL查询格式"
}