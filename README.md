# SQL Query API

A FastAPI-based HTTP API for executing SQL queries with a web interface for testing.

## Features

- HTTP API endpoint for executing SQL queries
- API key authentication
- Support for markdown-formatted SQL queries
- Multiple response formats (JSON, Markdown table, CSV)
- Web interface for API documentation and testing
- JSON response formatting and copying
- Error handling and detailed error messages

## Setup

### Method 1: Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
Create a `.env` file with the following variables:
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

3. Run the application:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Method 2: Docker Setup

1. Configure environment variables:
Create a `.env` file with the same variables as shown above.

2. Build and run with Docker:
```bash
# Build the Docker image
docker build -t sql-query-api .

# Run the container
docker run -d \
  --name sql-query-api \
  -p 8000:8000 \
  --env-file .env \
  sql-query-api
```

### Method 3: Docker Compose Setup (Recommended)

1. Configure environment variables:
Create a `.env` file with the same variables as shown above.

2. Run with Docker Compose:
```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

The application will be available at `http://localhost:8000`.

## Usage

### Web Interface

Access the web interface by opening `http://localhost:8000` in your browser.

### API Endpoint

**Endpoint:** `/query`
**Method:** POST
**Headers:**
- `X-API-Key`: Your API key
- `Content-Type`: application/json

**Request Body:**
```json
{
    "markdown_text": "Your SQL query in markdown format",
    "response_format": "json"  // Optional, defaults to "json". Can be "json", "markdown", or "csv"
}
```

**Example Requests:**

1. JSON format (default):
```bash
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"markdown_text": "```sql\nSELECT now() AS now;\n```", "response_format": "json"}'
```

2. Markdown table format:
```bash
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"markdown_text": "```sql\nSELECT now() AS now;\n```", "response_format": "markdown"}'
```

3. CSV format:
```bash
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"markdown_text": "```sql\nSELECT now() AS now;\n```", "response_format": "csv"}'
```

**Response Format:**

The response format depends on the `response_format` parameter in your request:

1. JSON format (default):
```json
{
    "code": 200,
    "message": "success",
    "data": [
        // Query results as JSON array
    ]
}
```

2. Markdown table format:
```json
{
    "code": 200,
    "message": "success",
    "data": "| Column1 | Column2 |\n|---------|----------|\n| value1  | value2   |"
}
```

3. CSV format:
```json
{
    "code": 200,
    "message": "success",
    "data": "Column1,Column2\nvalue1,value2"
}
```

**Response Codes:**

| Code | Message | Description |
|------|---------|-------------|
| 200 | success | Query executed successfully |
| 400 | bad_request | Invalid request format or parameters |
| 401 | unauthorized | Invalid or missing API key |
| 403 | forbidden | Insufficient permissions to execute the query |
| 404 | not_found | Requested resource not found |
| 422 | validation_error | Invalid SQL query syntax |
| 500 | internal_server_error | Server-side error during query execution |
| 503 | service_unavailable | Database connection error or service temporarily unavailable |

Each response will include:
- `code`: HTTP status code indicating the result of the request
- `message`: A brief description of the result
- `data`: Query results (for successful queries) or error details (for failed queries)

**Error Response Example:**
```json
{
    "code": 400,
    "message": "bad_request",
    "error": "Invalid SQL query format"
}
```