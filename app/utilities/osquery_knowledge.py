# Filepath: app/utilities/osquery_knowledge.py
# OSQuery Knowledge class for integration with the chat system

import logging
import time
from typing import Dict, Any, List, Optional
import json

from app.models import db, DeviceOSQuery, Devices
from app.utilities.app_logging_helper import log_with_route
from app.utilities.osquery_utils import OSQueryUtility
from app import safe_db_session

class OSQueryKnowledge:
    """Knowledge class for querying osquery data"""
    
    def __init__(self, device_uuid: str):
        self.device_uuid = device_uuid
        self.osquery_util = OSQueryUtility(device_uuid)
        self._cache = {}  # Add cache
        self._cache_timestamps = {}  # Track when each cache entry was created
        self._cache_ttl = 30  # Cache time-to-live in seconds
    
    def query(self, query_type: str, force_refresh: bool = False) -> dict:
        """Query osquery information based on type with caching"""
        query_type = query_type.lower()
        
        # Add debug logging
        logging.debug(f"OSQueryKnowledge query called for type '{query_type}'")
        
        # Check if cache entry is expired
        current_time = time.time()
        is_expired = (
            query_type in self._cache_timestamps and 
            current_time - self._cache_timestamps.get(query_type, 0) > self._cache_ttl
        )
        
        # Return cached result if valid
        if not force_refresh and query_type in self._cache and not is_expired:
            logging.debug(f"Returning cached result for {query_type}")
            return self._cache[query_type]
        
        try:
            result = None
            
            # Handle different query types
            if 'tables' in query_type or 'schema' in query_type:
                result = self._get_available_tables()
            elif 'natural' in query_type or 'nl' in query_type:
                # Extract the actual query from the input
                # Format expected: "natural:query" or "nl:query"
                query = query_type.split(':', 1)[1] if ':' in query_type else ""
                if not query:
                    return {"error": "No query provided. Use format 'natural:your query'"}
                result = self._process_natural_language(query, force_refresh)
            elif 'sql' in query_type:
                # Format expected: "sql:SELECT * FROM processes"
                sql = query_type.split(':', 1)[1] if ':' in query_type else ""
                if not sql:
                    return {"error": "No SQL provided. Use format 'sql:SELECT * FROM table'"}
                result = self._execute_sql(sql, force_refresh)
            elif 'stored' in query_type:
                # Get stored query results
                # Format expected: "stored:query_name"
                query_name = query_type.split(':', 1)[1] if ':' in query_type else ""
                if not query_name:
                    return {"error": "No query name provided. Use format 'stored:query_name'"}
                result = self._get_stored_query(query_name, force_refresh)
            else:
                return {"error": f"Unknown query type: {query_type}"}
            
            # Cache successful results
            if result and 'error' not in result:
                logging.debug(f"Caching result for {query_type}")
                self._cache[query_type] = result
                self._cache_timestamps[query_type] = current_time
            return result
            
        except Exception as e:
            logging.error(f"Error querying osquery info: {str(e)}")
            return {"error": str(e)}
    
    def clear_cache(self, query_type: Optional[str] = None) -> None:
        """Clear the entire cache or just a specific query type"""
        if query_type:
            if query_type in self._cache:
                del self._cache[query_type]
                if query_type in self._cache_timestamps:
                    del self._cache_timestamps[query_type]
                logging.debug(f"Cleared cache entry for {query_type}")
        else:
            self._cache = {}
            self._cache_timestamps = {}
            logging.debug("Cleared entire osquery knowledge cache")
    
    def _get_available_tables(self) -> dict:
        """Get available osquery tables"""
        tables = self.osquery_util.get_available_tables(force_refresh=True)
        
        if not tables:
            return {"error": "No osquery tables available"}
        
        # Format the tables for display
        table_list = []
        for table in tables:
            table_name = table.get('name', 'unknown')
            table_list.append(table_name)
        
        return {
            "type": "osquery_tables",
            "tables": table_list,
            "count": len(table_list)
        }
    
    def _process_natural_language(self, query: str, force_refresh: bool = False) -> dict:
        """Process a natural language query"""
        result = self.osquery_util.process_natural_language_query(query, force_refresh)
        
        if 'error' in result:
            return result
        
        return {
            "type": "osquery_natural_language",
            "query": result.get('query', ''),
            "sql": result.get('sql', ''),
            "result": result.get('result', {})
        }
    
    def _execute_sql(self, sql: str, force_refresh: bool = False) -> dict:
        """Execute an SQL query directly"""
        result = self.osquery_util.execute_query(sql, force_refresh)
        
        return {
            "type": "osquery_sql",
            "sql": sql,
            "result": result
        }
    
    def _get_stored_query(self, query_name: str, force_refresh: bool = False) -> dict:
        """Get stored query results"""
        with safe_db_session() as session:
            query_data = session.query(DeviceOSQuery).filter_by(
                deviceuuid=self.device_uuid,
                query_name=query_name
            ).first()
            
            if not query_data:
                return {"error": f"No data available for query '{query_name}'"}
            
            # Check if data is stale and force refresh is requested
            if force_refresh and (time.time() - query_data.last_updated > self._cache_ttl):
                # In a real implementation, this would trigger a refresh
                # For now, we'll just return the stale data with a warning
                return {
                    "type": "osquery_stored",
                    "query_name": query_name,
                    "data": query_data.query_data,
                    "warning": "Data may be stale"
                }
            
            return {
                "type": "osquery_stored",
                "query_name": query_name,
                "data": query_data.query_data
            }
