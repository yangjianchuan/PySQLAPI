from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import re
from typing import Optional, Literal
from pydantic import BaseModel
import json
from datetime import datetime, date
from decimal import Decimal
import csv
from io import StringIO

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

class QueryRequest(BaseModel):
    markdown_text: str
    response_format: Optional[Literal["json", "markdown", "csv"]] = "json"

def get_db_connection():
    """Create and return a database connection"""
    config = {
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT')),
        'database': os.getenv('MYSQL_DATABASE'),
        'raise_on_warnings': os.getenv('MYSQL_RAISE_ON_WARNINGS') == 'True',
        'auth_plugin': os.getenv('MYSQL_AUTH_PLUGIN'),
        'connection_timeout': int(os.getenv('MYSQL_CONNECTION_TIMEOUT'))
    }
    return mysql.connector.connect(**config)

def extract_sql_from_markdown(text: str) -> str:
    """Extract SQL query from markdown text"""
    # Clean HTML placeholders and escape characters
    clean_text = text
    
    # Handle escaped characters
    escape_chars = {
        '\\n': '\n',
        '\\"': '"',
        "\\'": "'",
        '\\`': '`',
        '\\_': '_',
        '\\*': '*',
        '\\\\': '\\'
    }
    
    for escape, char in escape_chars.items():
        clean_text = clean_text.replace(escape, char)
    
    # Try to find SQL in code blocks with SQL language specification
    sql_match = re.search(r'```sql\s*(.*?)\s*```', clean_text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Try to find SQL in generic code blocks
    code_match = re.search(r'```\s*(.*?)\s*```', clean_text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    
    # If no code blocks found, return the text as is (assuming it's a direct SQL query)
    return clean_text.strip()

def execute_sql(sql: str):
    """Execute SQL query and return results"""
    try:
        # Add Match class for regex matching simulation
        class Match:
            def __init__(self, string, start, end, groups):
                self.string = string
                self.start = lambda: start
                self.end = lambda: end
                self._groups = groups
            
            def group(self, index):
                return self._groups[index] if index < len(self._groups) else None

        # Clean up SQL query by removing newlines, backslashes and normalizing spaces
        cleaned_sql = sql.strip()
        
        # First handle escaped newlines and spaces
        cleaned_sql = cleaned_sql.replace('\\\n', '\n').replace('\\ ', ' ')
        
        # Handle escaped characters
        cleaned_sql = cleaned_sql.replace('\\*', '*')
        cleaned_sql = cleaned_sql.replace('\\_', '_')
        cleaned_sql = cleaned_sql.replace('\\`', '`')
        
        # Handle escaped quotes - convert to regular quotes
        cleaned_sql = re.sub(r'\\"([^"]*)\\"', r'"\1"', cleaned_sql)  # Handle \"...\"
        cleaned_sql = re.sub(r"\\'([^']*)\\'", r"'\1'", cleaned_sql)  # Handle \'...\'
        cleaned_sql = cleaned_sql.replace('\\"', '"')
        cleaned_sql = cleaned_sql.replace("\\'", "'")
        
        # Fix double percentage signs in date format strings
        cleaned_sql = re.sub(r"(DATE_FORMAT\([^,]+,\s*)'%%([^']*)'", r"\1'%\2'", cleaned_sql)
        
        # Handle DATE_FORMAT with specific format string cleaning - preserve original format
        def clean_date_format(match):
            column = match.group(1).strip()
            format_string = match.group(2)
            # Keep the original format string, just clean up any extra spaces around it
            format_string = format_string.strip()
            return f"DATE_FORMAT({column},'{format_string}')"
            
        cleaned_sql = re.sub(r"DATE_FORMAT\s*\(\s*([^,]+)\s*,\s*'([^']+)'\s*\)", 
                           clean_date_format, 
                           cleaned_sql)
        
        # Clean column names with quotes
        def clean_column_name(match):
            quote = match.group(1)
            column = match.group(2)
            cleaned_column = column.strip()
            return f"{quote}{cleaned_column}{quote}"
        
        cleaned_sql = re.sub(r"([`'\"])\s*([^`'\"]+?)\s*\1", clean_column_name, cleaned_sql)
        
        # Store alias mapping for later use
        alias_mapping = {}
        
        # Clean AS aliases
        def clean_alias(match):
            expr = match.group(1)
            alias = next((g for g in (match.group(2), match.group(3), match.group(4)) if g is not None), '')
            if not alias:
                return expr
            
            cleaned_alias = alias.strip()
            
            if match.group(3):  # Single quotes
                alias_mapping[cleaned_alias] = f"'{cleaned_alias}'"
            elif match.group(4):  # Backticks
                alias_mapping[cleaned_alias] = f"`{cleaned_alias}`"
            else:  # Double quotes or no quotes
                alias_mapping[cleaned_alias] = f"\"{cleaned_alias}\""
            
            return f"{expr} AS {alias_mapping[cleaned_alias]}"
        
        cleaned_sql = re.sub(
            r'(\S+)\s+AS\s+(?:([a-zA-Z0-9_\u4e00-\u9fff]+)|\'([^\']+)\'|`([^`]+)`)',
            clean_alias,
            cleaned_sql,
            flags=re.IGNORECASE
        )
        
        # Add spaces around SQL keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'JOIN',
                   'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'WITH', 'AS', 'ON', 'AND', 'OR',
                   'IN', 'NOT', 'NULL', 'IS', 'OVER', 'PARTITION BY']
        
        pattern = r'\b(' + '|'.join(keywords) + r')\b'
        cleaned_sql = re.sub(pattern, r' \1 ', cleaned_sql, flags=re.IGNORECASE)
        
        # Add spaces around operators
        operators = [r'=', r'<', r'>', r'<=', r'>=', r'<>', r'\+', r'-', r'\*', r'/']
        for op in operators:
            cleaned_sql = re.sub(fr'(?<!\s){op}(?!\s)', f' {op} ', cleaned_sql)
        
        # Fix multiple spaces
        cleaned_sql = re.sub(r'\s+', ' ', cleaned_sql)
        
        # Fix parentheses spacing
        cleaned_sql = re.sub(r'\(\s+', '(', cleaned_sql)
        cleaned_sql = re.sub(r'\s+\)', ')', cleaned_sql)
        
        # Clean dots in qualified names
        cleaned_sql = re.sub(r'\s*\.\s*', '.', cleaned_sql)
        
        # Clean GROUP BY and ORDER BY clauses
        def clean_by_clause(match):
            clause = match.group(1)
            columns = match.group(2).split(',')
            cleaned_columns = []
            for col in columns:
                col = col.strip()
                
                if '(' in col or ')' in col:
                    cleaned_columns.append(col)
                else:
                    if col.startswith('"') and col.endswith('"'):
                        inner_content = col[1:-1].strip()
                        cleaned_columns.append(f"\"{inner_content}\"")
                    elif col.startswith("'") and col.endswith("'"):
                        inner_content = col[1:-1].strip()
                        cleaned_columns.append(f"'{inner_content}'")
                    elif col.startswith('`') and col.endswith('`'):
                        inner_content = col[1:-1].strip()
                        cleaned_columns.append(f"`{inner_content}`")
                    else:
                        cleaned_columns.append(col.strip())
            
            return f"{clause} {', '.join(cleaned_columns)}"
        
        # Clean GROUP BY clause
        cleaned_sql = re.sub(r'(GROUP BY)\s+([^()]+?)(?=\s+HAVING|\s+ORDER BY|\s+LIMIT|$)', 
                           clean_by_clause, 
                           cleaned_sql, 
                           flags=re.IGNORECASE)
        
        # Clean ORDER BY clause
        cleaned_sql = re.sub(r'(ORDER BY)\s+([^()]+?)(?=\s+LIMIT|$)', 
                           clean_by_clause, 
                           cleaned_sql, 
                           flags=re.IGNORECASE)
        
        # Ensure HAVING keyword has proper spacing
        cleaned_sql = re.sub(r'\s*HAVING\s*', ' HAVING ', cleaned_sql, flags=re.IGNORECASE)

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            cursor.execute(cleaned_sql)
            results = cursor.fetchall()
            
            # Convert Decimal to float in results
            for row in results:
                for key, value in row.items():
                    if isinstance(value, Decimal):
                        row[key] = float(value)
            
            return results
        except Error as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": str(e),
                    "sql_state": e.sqlstate if hasattr(e, 'sqlstate') else None,
                    "errno": e.errno if hasattr(e, 'errno') else None,
                    "executed_query": cleaned_sql
                }
            )
        finally:
            cursor.close()
            
    except Error as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Database connection error: {str(e)}",
                "connection_error": True
            }
        )
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

def convert_to_markdown_table(data):
    if not data:
        return ""
    
    # Get headers from first row
    headers = list(data[0].keys())
    
    # Create header row
    markdown = "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---" for _ in headers]) + " |\n"
    
    # Add data rows
    for row in data:
        markdown += "| " + " | ".join(str(row.get(header, "")) for header in headers) + " |\n"
    
    return markdown

def convert_to_csv(data):
    if not data:
        return ""
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()

@app.post("/query")
async def query_endpoint(request: Request, query: QueryRequest):
    # Verify API key from header
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != os.getenv('API_KEY'):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Extract SQL from markdown
    sql = extract_sql_from_markdown(query.markdown_text)
    if not sql:
        raise HTTPException(status_code=400, detail="No SQL query found in the input")
    
    try:
        # Execute SQL and get results
        results = execute_sql(sql)
        
        # Format results based on response_format
        formatted_data = results
        if query.response_format == "markdown":
            formatted_data = convert_to_markdown_table(results)
        elif query.response_format == "csv":
            formatted_data = convert_to_csv(results)
        
        # Return formatted response
        return {
            "code": 200,
            "message": "success",
            "data": formatted_data
        }
    except HTTPException as e:
        return {
            "code": e.status_code,
            "message": "error",
            "data": e.detail
        }
    except Exception as e:
        return {
            "code": 500,
            "message": "error",
            "data": str(e)
        }

# Mount static files for the HTML interface
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_html():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)