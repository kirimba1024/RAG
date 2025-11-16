import os
from urllib.parse import urlparse
from sqlalchemy import create_engine, text

_ENGINES = {}

def load_db_connections():
    connections = {}
    idx = 1
    while True:
        url = os.getenv(f"DB_{idx}_URL")
        if not url:
            break
        username = os.getenv(f"DB_{idx}_USERNAME")
        password = os.getenv(f"DB_{idx}_PASSWORD")
        description = os.getenv(f"DB_{idx}_DESCRIPTION")
        tool_name = os.getenv(f"DB_{idx}_TOOL_NAME")
        if username and password and tool_name:
            connections[tool_name] = {
                "url": url,
                "username": username,
                "password": password,
                "description": description
            }
        idx += 1
    return connections

DB_CONNECTIONS = load_db_connections()

def _sqlalchemy_url(conn: dict) -> str:
    raw = (conn.get("url") or "").strip().removeprefix("jdbc:")
    if "://" not in raw:
        raw = "//" + raw
    parsed = urlparse(raw)
    scheme = parsed.scheme or "postgresql"
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    db = (parsed.path or "").lstrip("/") or conn.get("db_name", "")
    return f"{scheme}://{conn['username']}:{conn['password']}@{host}{port}/{db}"

def get_engine(tool_name: str):
    if tool_name in _ENGINES:
        return _ENGINES[tool_name]
    conn = DB_CONNECTIONS[tool_name]
    url = _sqlalchemy_url(conn)
    connect_args = {}
    if url.startswith("postgresql"):
        connect_args = {"options": "-c statement_timeout=30s"}
    engine = create_engine(url, connect_args=connect_args)
    _ENGINES[tool_name] = engine
    return engine

def db_query(tool_name, select):
    if not select.strip().upper().startswith("SELECT"):
        return {"error": "Разрешены только SELECT запросы", "rows": [], "select": select}
    try:
        engine = get_engine(tool_name)
        with engine.connect() as connection:
            result = connection.execute(text(select))
            rows = [dict(row._mapping) for row in result]
        return {"rows": rows, "select": select}
    except Exception as e:
        return {"error": str(e), "rows": [], "select": select}

