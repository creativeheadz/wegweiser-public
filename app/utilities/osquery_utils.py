# Filepath: app/utilities/osquery_utils.py
# Utility for handling osquery operations

import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
import re
import uuid

from flask import current_app
from langchain_openai import AzureChatOpenAI

from app.models import db, DeviceOSQuery, Devices
from app.utilities.app_logging_helper import log_with_route
from app import safe_db_session

class OSQueryUtility:
    """Utility for handling osquery operations including natural language translation"""

    def __init__(self, device_uuid: str):
        self.device_uuid = device_uuid
        self._cache = {}  # Cache for query results
        self._cache_timestamps = {}  # Track when each cache entry was created
        self._cache_ttl = 30  # Cache time-to-live in seconds
        self._tables_cache = None  # Cache for available tables
        self._tables_cache_timestamp = 0
        self._tables_cache_ttl = 3600  # Tables cache TTL (1 hour)

    def get_available_tables(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get available osquery tables on the device"""
        current_time = time.time()
        is_expired = current_time - self._tables_cache_timestamp > self._tables_cache_ttl

        if not force_refresh and self._tables_cache and not is_expired:
            return self._tables_cache

        # Query the schema table to get all available tables
        with safe_db_session() as session:
            schema_data = session.query(DeviceOSQuery).filter_by(
                deviceuuid=self.device_uuid,
                query_name='schema'
            ).first()
            # Fallback: try UUID object compare in case type mismatch prevents match
            if not schema_data:
                try:
                    schema_data = session.query(DeviceOSQuery).filter_by(
                        deviceuuid=uuid.UUID(str(self.device_uuid)),
                        query_name='schema'
                    ).first()
                except Exception:
                    schema_data = None

            if not schema_data:
                log_with_route(logging.WARNING, f"No schema data available for device {self.device_uuid}")
                return []

            tables = schema_data.query_data
            self._tables_cache = tables
            self._tables_cache_timestamp = current_time
            return tables

    def translate_to_sql(self, natural_language_query: str) -> str:
        """Translate natural language query to SQL using LLM"""
        try:
            # Handle common queries directly without using LLM
            query_lower = natural_language_query.lower()

            # Discover available tables for targeted mappings
            tables = self.get_available_tables()
            table_names: Set[str] = set()
            for t in (tables or []):
                name = (t or {}).get('name')
                if name:
                    table_names.add(str(name).lower())

            def has(name: str) -> bool:
                return name.lower() in table_names

            def first_available(names: List[str]) -> Optional[str]:
                for n in names:
                    if has(n):
                        return n
                return None

            # Direct mapping for common user-related queries
            if any(pattern in query_lower for pattern in ["list all user accounts", "extract users", "show all users", "get users", "user accounts"]):
                sql_query = "SELECT username, uid, gid, description, directory, shell FROM users ORDER BY uid LIMIT 50"
                log_with_route(logging.INFO, f"Direct mapping for '{natural_language_query}' to SQL: {sql_query}")
                return sql_query

            # Direct mapping for common process-related queries (portable columns)
            if any(pattern in query_lower for pattern in ["list all running processes", "show all processes", "get processes", "running processes"]):
                sql_query = "SELECT pid, name, cmdline, uid FROM processes ORDER BY pid LIMIT 50"
                log_with_route(logging.INFO, f"Direct mapping for '{natural_language_query}' to SQL: {sql_query}")
                return sql_query

            # Direct mapping for common service-related queries (platform-aware)
            if any(pattern in query_lower for pattern in ["list all services", "show all services", "get services", "running services"]):
                svc = first_available(["services", "systemd_units", "launchd"])
                if svc == "services":
                    sql_query = "SELECT name, status, start_type, path FROM services ORDER BY name LIMIT 50"
                elif svc == "systemd_units":
                    sql_query = "SELECT name, load_state, active_state, sub_state FROM systemd_units ORDER BY name LIMIT 50"
                elif svc == "launchd":
                    sql_query = "SELECT label, program FROM launchd LIMIT 50"
                else:
                    # Fallback to a safe generic processes view
                    sql_query = "SELECT pid, name, cmdline FROM processes LIMIT 25"
                log_with_route(logging.INFO, f"Direct mapping for '{natural_language_query}' to SQL: {sql_query}")
                return sql_query

            # Direct mapping for common software-related queries (platform-aware)
            if any(pattern in query_lower for pattern in ["list all installed software", "show all software", "get software", "installed software"]):
                sw = first_available(["programs", "deb_packages", "rpm_packages", "apps", "homebrew_packages"])
                if sw == "programs":
                    sql_query = "SELECT name, version, install_location, install_date FROM programs ORDER BY name LIMIT 100"
                elif sw == "deb_packages":
                    sql_query = "SELECT name, version FROM deb_packages ORDER BY name LIMIT 100"
                elif sw == "rpm_packages":
                    sql_query = "SELECT name, version, release FROM rpm_packages ORDER BY name LIMIT 100"
                elif sw == "apps":
                    sql_query = "SELECT name, bundle_identifier, path FROM apps ORDER BY name LIMIT 100"
                elif sw == "homebrew_packages":
                    sql_query = "SELECT name, version FROM homebrew_packages ORDER BY name LIMIT 100"
                else:
                    sql_query = "SELECT name FROM sqlite_master WHERE type='table' LIMIT 50"
                log_with_route(logging.INFO, f"Direct mapping for '{natural_language_query}' to SQL: {sql_query}")
                return sql_query

            # Logged-in users (no process context)
            if any(pattern in query_lower for pattern in [
                "who is logged in", "who is logged on", "current users", "active users", "logged in users", "logged on users"
            ]):
                if has("logged_in_users"):
                    sql_query = "SELECT username, tty, time FROM logged_in_users ORDER BY time DESC LIMIT 50"
                elif has("users"):
                    sql_query = "SELECT username, uid FROM users ORDER BY uid LIMIT 50"
                else:
                    sql_query = "SELECT pid, name, cmdline FROM processes LIMIT 25"
                log_with_route(logging.INFO, f"Direct mapping for '{natural_language_query}' to SQL: {sql_query}")
                return sql_query

            # System uptime
            if ("uptime" in query_lower) or (("how long" in query_lower) and ("up" in query_lower)) or ("system boot" in query_lower) or ("boot time" in query_lower):
                if has("uptime"):
                    sql_query = "SELECT days, hours, minutes, seconds, total_seconds FROM uptime"
                else:
                    sql_query = "SELECT name, version FROM os_version LIMIT 1"
                log_with_route(logging.INFO, f"Direct mapping for '{natural_language_query}' to SQL: {sql_query}")
                return sql_query

            # Logged-in users and their processes
            if ("logged in" in query_lower or "logged on" in query_lower) and ("process" in query_lower):
                if has("logged_in_users"):
                    sql_query = (
                        "SELECT liu.username AS user, p.pid, p.name, p.cmdline "
                        "FROM logged_in_users liu "
                        "JOIN processes p ON p.uid = liu.uid "
                        "ORDER BY liu.username, p.pid LIMIT 100"
                    )
                else:
                    # Fallback: join users to label owners, not filtering to currently logged-in
                    if has("users"):
                        sql_query = (
                            "SELECT u.username AS user, p.pid, p.name, p.cmdline "
                            "FROM processes p LEFT JOIN users u ON p.uid = u.uid "
                            "ORDER BY u.username, p.pid LIMIT 100"
                        )
                    else:
                        sql_query = "SELECT pid, name, cmdline, uid FROM processes ORDER BY pid LIMIT 100"
                log_with_route(logging.INFO, f"Direct mapping for '{natural_language_query}' to SQL: {sql_query}")
                return sql_query

            # For other queries, use the LLM
            # Get available tables for context (use cached above)
            table_info = self._format_table_info(tables)

            # Create LLM instance
            llm = AzureChatOpenAI(
                openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
                azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
                azure_deployment="wegweiser",
                openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
            )

            # Create prompt for SQL translation
            prompt = f"""You are an expert in translating natural language queries into SQL for osquery.
Given the following osquery tables and their schemas, generate a SQL query that answers the user's question.
Only use the tables and columns that are available in the schema provided.
Keep the query simple and efficient. Use LIMIT clauses when appropriate to avoid returning too many rows.

Available tables and their schemas:
{table_info}

User's question: {natural_language_query}

Respond with ONLY the SQL query, nothing else. Do not include any explanations or markdown formatting.
"""

            # Get SQL query from LLM
            response = llm.invoke(prompt)
            sql_query = response.content.strip()

            # Clean up the SQL query (remove any markdown formatting if present)
            candidate = re.sub(r'^```sql\s*', '', sql_query)
            candidate = re.sub(r'\s*```$', '', candidate)
            candidate = candidate.strip()
            # Normalize whitespace
            candidate = re.sub(r"\s+", " ", candidate).strip()

            lower = candidate.lower()
            # Allow SELECT, CTEs that start with WITH, and meta commands
            if not (lower.startswith('select') or lower.startswith('with') or lower.startswith('.tables') or lower.startswith('.schema')):
                # Heuristic fallback for common intents if LLM didn't return SQL
                ql = query_lower
                fallback_sql = None
                if (("logged in" in ql) or ("logged on" in ql) or ("login" in ql) or ("logged-in" in ql) or ("logged-on" in ql)) and ("process" not in ql):
                    if has("logged_in_users"):
                        fallback_sql = "SELECT username, tty, time FROM logged_in_users ORDER BY time DESC LIMIT 50"
                    elif has("users"):
                        fallback_sql = "SELECT username, uid FROM users ORDER BY uid LIMIT 50"
                elif ("uptime" in ql) or (("how long" in ql) and ("up" in ql)) or (("boot" in ql) and ("when" in ql)):
                    if has("uptime"):
                        fallback_sql = "SELECT days, hours, minutes, seconds, total_seconds FROM uptime"
                elif any(t in ql for t in ["software", "packages", "apps", "applications"]):
                    sw = first_available(["programs", "deb_packages", "rpm_packages", "apps", "homebrew_packages"])
                    if sw == "programs":
                        fallback_sql = "SELECT name, version, install_location, install_date FROM programs ORDER BY name LIMIT 100"
                    elif sw == "deb_packages":
                        fallback_sql = "SELECT name, version FROM deb_packages ORDER BY name LIMIT 100"
                    elif sw == "rpm_packages":
                        fallback_sql = "SELECT name, version, release FROM rpm_packages ORDER BY name LIMIT 100"
                    elif sw == "apps":
                        fallback_sql = "SELECT name, bundle_identifier, path FROM apps ORDER BY name LIMIT 100"
                    elif sw == "homebrew_packages":
                        fallback_sql = "SELECT name, version FROM homebrew_packages ORDER BY name LIMIT 100"
                if not fallback_sql:
                    fallback_sql = "SELECT pid, name, cmdline FROM processes LIMIT 25"
                log_with_route(logging.WARNING, f"LLM returned non-SQL. Using fallback for '{natural_language_query}': {fallback_sql}")
                return fallback_sql

            log_with_route(logging.INFO, f"Translated '{natural_language_query}' to SQL: {candidate}")
            return candidate

        except Exception as e:
            log_with_route(logging.ERROR, f"Error translating to SQL: {str(e)}")
            # Safe fallback so the UI doesn't get a 400 when translation fails
            return "SELECT pid, name, cmdline FROM processes LIMIT 25"

    def execute_query(self, sql_query: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Execute an osquery SQL query on the device"""
        # Check cache first
        cache_key = f"sql:{sql_query}"
        current_time = time.time()
        is_expired = (
            cache_key in self._cache_timestamps and
            current_time - self._cache_timestamps.get(cache_key, 0) > self._cache_ttl
        )

        if not force_refresh and cache_key in self._cache and not is_expired:
            return self._cache[cache_key]

        # Import here to avoid circular imports
        from app.routes.ws.agent_endpoint import send_osquery_command, active_connections

        # Check if device is connected
        if self.device_uuid not in active_connections:
            return {
                "status": "error",
                "message": "Device not connected",
                "query": sql_query
            }

        # Generate a unique query name for this ad-hoc query
        query_name = f"ad_hoc_{int(current_time)}"

        # Send command to agent
        success = send_osquery_command(self.device_uuid, sql_query, query_name)

        if not success:
            result = {
                "status": "error",
                "message": "Failed to send query to device",
                "query": sql_query
            }
        else:
            result = {
                "status": "pending",
                "message": "Query sent to device",
                "query": sql_query,
                "query_name": query_name
            }

        # Cache the result
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = current_time

        return result

    def process_natural_language_query(self, query: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Process a natural language query and return results"""
        try:
            # Check if this is an osquery request
            if not self._is_osquery_request(query):
                return {"error": "Not an osquery request"}

            # Extract the actual query part
            clean_query = self._extract_query(query)

            # Translate to SQL
            sql_query = self.translate_to_sql(clean_query)
            if not sql_query:
                return {"error": "Failed to translate query to SQL"}

            # Execute the query
            result = self.execute_query(sql_query, force_refresh)

            return {
                "query": clean_query,
                "sql": sql_query,
                "result": result
            }

        except Exception as e:
            log_with_route(logging.ERROR, f"Error processing natural language query: {str(e)}")
            return {"error": str(e)}

    def _is_osquery_request(self, query: str) -> bool:
        """Determine if a query is an osquery request"""
        query_lower = query.lower()

        # Direct osquery indicators
        osquery_indicators = [
            "osquery",
            "from osquery",
            "using osquery",
            "with osquery",
            "system information",
            "system info",
            "system query"
        ]

        # Common system information requests that should use osquery
        system_info_patterns = [
            "extract users",
            "list users",
            "show users",
            "get users",
            "user accounts",
            "list processes",
            "show processes",
            "get processes",
            "running processes",
            "system processes",
            "list services",
            "show services",
            "get services",
            "running services",
            "system services",
            "installed software",
            "list software",
            "show software",
            "get software",
            "system hardware",
            "hardware info"
        ]

        # Check for direct osquery indicators
        if any(indicator in query_lower for indicator in osquery_indicators):
            return True

        # Check for system information patterns
        return any(pattern in query_lower for pattern in system_info_patterns)

    def _extract_query(self, query: str) -> str:
        """Extract the actual query part from the user's message"""
        query_lower = query.lower()

        # Remove osquery prefixes
        for prefix in ["from osquery", "using osquery", "with osquery", "osquery"]:
            if prefix in query_lower:
                # Find the position of the prefix and extract everything after it
                pos = query_lower.find(prefix) + len(prefix)
                query = query[pos:].strip()
                # Remove "please" if it's the first word
                if query.lower().startswith("please"):
                    query = query[7:].strip()
                break

        # Map common natural language queries to more specific osquery-friendly queries
        query_lower = query.lower()

        # Users-related queries
        if any(pattern in query_lower for pattern in ["extract users", "list users", "show users", "get users", "user accounts"]):
            return "list all user accounts on the system"

        # Processes-related queries
        if any(pattern in query_lower for pattern in ["list processes", "show processes", "get processes", "running processes"]):
            return "list all running processes with their details"

        # Services-related queries
        if any(pattern in query_lower for pattern in ["list services", "show services", "get services", "running services"]):
            return "list all services and their status"

        # Software-related queries
        if any(pattern in query_lower for pattern in ["installed software", "list software", "show software", "get software"]):
            return "list all installed software with version information"

        # If no specific mapping, return the cleaned query
        return query

    def _format_table_info(self, tables: List[Dict[str, Any]]) -> str:
        """Format table information for the LLM prompt"""
        if not tables:
            # Provide a minimal cross-platform subset so the LLM can still produce useful SQL
            return (
                "Table: processes\n"
                "Columns:\n"
                "  - pid (INTEGER)\n  - name (TEXT)\n  - cmdline (TEXT)\n  - uid (INTEGER)\n\n"
                "Table: users\n"
                "Columns:\n"
                "  - username (TEXT)\n  - uid (INTEGER)\n  - gid (INTEGER)\n\n"
                "Table: logged_in_users\n"
                "Columns:\n"
                "  - username (TEXT)\n  - uid (INTEGER)\n  - tty (TEXT)\n  - time (INTEGER)"
            )

        formatted_info = []
        for table in tables:
            table_name = table.get('name', 'unknown')
            columns = table.get('columns', [])

            column_info = []
            for column in columns:
                column_name = column.get('name', 'unknown')
                column_type = column.get('type', 'unknown')
                column_info.append(f"  - {column_name} ({column_type})")

            formatted_table = f"Table: {table_name}\nColumns:\n" + "\n".join(column_info)
            formatted_info.append(formatted_table)

        return "\n\n".join(formatted_info)
