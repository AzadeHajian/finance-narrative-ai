#!/usr/bin/env python3
"""
Supabase MCP Server - A Model Context Protocol server for Supabase/PostgreSQL
Provides tools to explore and query the database via stdio transport.

Spawned automatically as a subprocess by mcp_server/client.py — no need
to run this file manually.
"""

import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from supabase import create_client, Client

load_dotenv()

mcp = FastMCP("supabase")


def _get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url:
        raise ValueError("SUPABASE_URL not found in .env")
    if not key:
        raise ValueError("SUPABASE_ANON_KEY not found in .env")
    return create_client(url, key)


@mcp.tool()
def list_tables() -> str:
    """
    List all tables in the Supabase database.
    Always call this first before writing any SQL query
    so you know what tables are available.
    """
    try:
        client = _get_client()
        response = client.rpc("execute_sql", {
            "query": """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """
        }).execute()
        return str(response.data)
    except Exception as e:
        return f"Error listing tables: {e}"


@mcp.tool()
def get_table_schema(table_name: str) -> str:
    """
    Get the column names and data types of a specific table.
    Call this before writing a SQL query so you know
    exactly what columns exist and their types.

    Args:
        table_name: Name of the table to inspect.
    """
    try:
        client = _get_client()
        response = client.rpc("execute_sql", {
            "query": f"""
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = '{table_name}'
                ORDER BY ordinal_position;
            """
        }).execute()
        if not response.data:
            return f"Table '{table_name}' not found or has no columns."
        return str(response.data)
    except Exception as e:
        return f"Error getting schema for '{table_name}': {e}"


@mcp.tool()
def get_sample_rows(table_name: str) -> str:
    """
    Get the first 5 rows of a table as a preview.
    Use this to understand what kind of data is in
    the table before generating a SQL query.

    Args:
        table_name: Name of the table to preview.
    """
    try:
        client = _get_client()
        response = client.rpc("execute_sql", {
            "query": f"SELECT * FROM {table_name} LIMIT 5;"
        }).execute()
        if not response.data:
            return f"Table '{table_name}' is empty or does not exist."
        return str(response.data)
    except Exception as e:
        return f"Error getting sample rows for '{table_name}': {e}"


@mcp.tool()
def execute_sql(query: str) -> str:
    """
    Execute a raw SQL query against the Supabase database.
    Use this to run the final SQL after you have explored
    the tables and schema using the other tools.

    Only use SELECT statements unless the user explicitly
    asks to insert, update, or delete data.

    Args:
        query: The SQL query to execute.
    """
    try:
        client = _get_client()
        response = client.rpc("execute_sql", {
            "query": query
        }).execute()
        if not response.data:
            return "Query executed successfully but returned no results."
        return str(response.data)
    except Exception as e:
        return f"SQL execution error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
