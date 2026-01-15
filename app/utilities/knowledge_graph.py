from typing import Dict, Any, List, Optional
from app.models import (
    db, DeviceStatus, DeviceDrives, DeviceMemory, 
    DeviceNetworks, DeviceCpu, DeviceGpu, Devices
)
import logging
import time
import requests
from bs4 import BeautifulSoup
import hashlib
from urllib.parse import quote_plus
from flask import current_app

class KnowledgeGraph:
    """Knowledge graph for querying device information"""
    
    def __init__(self, device_uuid: str):
        self.device_uuid = device_uuid
        self._cache = {}  # Add cache
        self._cache_timestamps = {}  # Track when each cache entry was created
        self._cache_ttl = 30  # Cache time-to-live in seconds
        self._web_cache = {}  # Separate cache for web results
        self._web_cache_ttl = 3600  # Web cache TTL (1 hour)

    def query(self, query_type: str, force_refresh: bool = False) -> dict:
        """Query device information based on type with caching"""
        query_type = query_type.lower()
        
        # Add debug logging with stack trace
        logging.debug(f"KnowledgeGraph query called for type '{query_type}' from:", stack_info=True)
        
        # Special handling for health-related queries
        if 'health' in query_type or 'score' in query_type:
            return self._get_health_info(force_refresh=True)
        
        # Check if cache entry is expired
        current_time = time.time()
        is_expired = (
            query_type in self._cache_timestamps and 
            current_time - self._cache_timestamps.get(query_type, 0) > self._cache_ttl
        )
        
        # Check cache first if not expired and not forcing refresh
        if query_type in self._cache and not is_expired and not force_refresh:
            logging.debug(f"Returning cached result for {query_type}")
            return self._cache[query_type]
        
        try:
            result = None
            # Handle web information retrieval requests
            if 'web' in query_type or 'internet' in query_type or 'search' in query_type:
                # Extract the search query from the input
                # Format expected: "web:search_query" or "web search:search_query"
                search_query = query_type.split(':', 1)[1] if ':' in query_type else ""
                if not search_query:
                    return {"error": "No search query provided. Use format 'web:your search query'"}
                result = self._get_web_information(search_query, force_refresh)
            elif 'storage' in query_type:
                result = self._get_storage_info()
            elif 'gpu' in query_type or 'graphics' in query_type:
                result = self._get_gpu_info()
            elif 'memory' in query_type or 'ram' in query_type:
                result = self._get_memory_info()
            elif 'network' in query_type:
                result = self._get_network_info()
            elif 'system' in query_type or 'cpu' in query_type:
                result = self._get_system_info()
            else:
                return {"error": f"Unknown query type: {query_type}"}

            # Cache successful results
            if result and 'error' not in result:
                logging.debug(f"Caching result for {query_type}")
                self._cache[query_type] = result
                self._cache_timestamps[query_type] = current_time
            return result

        except Exception as e:
            logging.error(f"Error querying device info: {str(e)}")
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
            logging.debug("Cleared entire knowledge graph cache")

    def _get_health_info(self, force_refresh: bool = False) -> dict:
        """Get health-related information with optional cache bypass"""
        cache_key = 'health'
        current_time = time.time()
        is_expired = (
            cache_key in self._cache_timestamps and 
            current_time - self._cache_timestamps.get(cache_key, 0) > self._cache_ttl
        )
        
        if not force_refresh and cache_key in self._cache and not is_expired:
            return self._cache[cache_key]
        
        device = Devices.query.get(self.device_uuid)
        if not device:
            return {"error": "Device not found"}
        
        # Get the latest health score from database
        db.session.refresh(device)  # Ensure we have the latest data
        
        result = {
            "type": "health",
            "health_score": device.health_score,
            "health_score_formatted": f"{device.health_score:.1f}%",
            "last_updated": getattr(device, 'health_score_updated_at', current_time)
        }
        
        # Cache the result
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = current_time
        
        return result

    def _get_storage_info(self) -> dict:
        """Get storage information"""
        drives = DeviceDrives.query.filter_by(deviceuuid=self.device_uuid).all()
        if not drives:
            return {"error": "No storage information available"}
            
        return {
            "type": "storage",
            "drives": [{
                "name": drive.drive_name,
                "total_gb": round(drive.drive_total / (1024**3), 2),
                "used_gb": round(drive.drive_used / (1024**3), 2),
                "free_gb": round(drive.drive_free / (1024**3), 2),
                "used_percentage": drive.drive_used_percentage
            } for drive in drives]
        }

    def _get_system_info(self) -> dict:
        """Get system information"""
        status = DeviceStatus.query.filter_by(deviceuuid=self.device_uuid).first()
        cpu = DeviceCpu.query.filter_by(deviceuuid=self.device_uuid).first()
        
        if not status:
            return {"error": "No system information available"}
        
        # Parse CPU name for additional details if available
        cpu_details = {
            "count": status.cpu_count,
            "usage": status.cpu_usage,
            "name": "Unknown",
            "manufacturer": "Unknown",
            "model": "Unknown",
            "speed": "Unknown",
            "cores": status.cpu_count,
            "last_update": None
        }
        
        if cpu and cpu.cpu_name:
            cpu_details["name"] = cpu.cpu_name
            cpu_details["last_update"] = cpu.last_update
            
            # Try to parse detailed info from CPU name
            # Example: "Intel(R) Core(TM) i7-9700K CPU @ 3.60GHz"
            try:
                name_parts = cpu.cpu_name.split()
                if "Intel" in cpu.cpu_name:
                    cpu_details["manufacturer"] = "Intel"
                    # Try to extract model and speed
                    for part in name_parts:
                        if "i" in part and "-" in part:  # e.g., "i7-9700K"
                            cpu_details["model"] = part
                        if "GHz" in part:  # e.g., "3.60GHz"
                            cpu_details["speed"] = part.strip("@").strip()
                elif "AMD" in cpu.cpu_name:
                    cpu_details["manufacturer"] = "AMD"
                    # Add AMD-specific parsing if needed
            except Exception as e:
                logging.warning(f"Could not parse detailed CPU info: {str(e)}")
        
        return {
            "type": "system",
            "platform": status.agent_platform,
            "name": status.system_name,
            "manufacturer": status.system_manufacturer,
            "model": status.system_model,
            "cpu": cpu_details,
            "boot_time": status.boot_time
        }

    def _get_memory_info(self) -> dict:
        """Get memory information"""
        logging.info(f"Querying memory info for device: {self.device_uuid}")
        memory = DeviceMemory.query.filter_by(deviceuuid=self.device_uuid).first()
        
        if not memory:
            logging.warning(f"No memory information found for device {self.device_uuid}")
            return {"error": "No memory information available"}
        
        # Log raw values from database
        logging.info(f"Raw memory values from DB: total={memory.total_memory}, "
                    f"used={memory.used_memory}, free={memory.free_memory}")
            
        result = {
            "type": "memory",
            "total_gb": round(memory.total_memory / (1024**3), 2),
            "used_gb": round(memory.used_memory / (1024**3), 2),
            "free_gb": round(memory.free_memory / (1024**3), 2),
            "used_percentage": memory.mem_used_percent
        }
        
        # Log converted values
        logging.info(f"Converted memory values: {result}")
        return result

    def _get_network_info(self) -> dict:
        """Get network information"""
        networks = DeviceNetworks.query.filter_by(deviceuuid=self.device_uuid).all()
        if not networks:
            return {"error": "No network information available"}
            
        return {
            "type": "network",
            "interfaces": [{
                "name": net.network_name,
                "status": "up" if net.if_is_up else "down",
                "speed": net.if_speed,
                "bytes_sent": net.bytes_sent,
                "bytes_received": net.bytes_rec,
                "errors_in": net.err_in,
                "errors_out": net.err_out
            } for net in networks]
        }

    def _get_gpu_info(self) -> dict:
        """Get GPU information"""
        gpu = DeviceGpu.query.filter_by(deviceuuid=self.device_uuid).first()
        if not gpu:
            return {"error": "No GPU information available"}
            
        return {
            "type": "gpu",
            "vendor": gpu.gpu_vendor,
            "product": gpu.gpu_product,
            "resolution": f"{gpu.gpu_hres}x{gpu.gpu_vres}",
            "color_depth": gpu.gpu_colour
        }

    def _get_web_information(self, search_query: str, force_refresh: bool = False) -> dict:
        """Get information from the web based on a search query with improved anti-CAPTCHA measures"""
        from app.utilities.app_logging_helper import log_with_route
        import traceback
        import random
        
        # Generate a cache key based on the search query
        cache_key = f"web:{hashlib.md5(search_query.encode()).hexdigest()}"
        current_time = time.time()
        
        # Check if we have a cached result that's not expired
        is_expired = (
            cache_key in self._web_cache and
            current_time - self._web_cache.get(cache_key, {}).get('timestamp', 0) > self._web_cache_ttl
        )
        
        if cache_key in self._web_cache and not is_expired and not force_refresh:
            log_with_route(logging.INFO, f"Returning cached web result for query: {search_query}", source_type="WebSearch")
            return self._web_cache[cache_key]['data']
        
        try:
            log_with_route(logging.INFO, f"Fetching web information for query: {search_query}", source_type="WebSearch")
            
            # Try Google search first since it has fewer CAPTCHA issues
            search_url = f"https://www.google.com/search?q={quote_plus(search_query)}"
            
            # Use a more sophisticated user agent that appears more legitimate
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            log_with_route(logging.DEBUG, f"Making request to: {search_url}", source_type="WebSearch")
            
            # Use a session to maintain cookies
            session = requests.Session()
            response = session.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse search results
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for CAPTCHA
            if "captcha" in response.text.lower() or "challenge" in response.text.lower() or "unusual traffic" in response.text.lower():
                log_with_route(logging.WARNING, "CAPTCHA detected on Google", source_type="WebSearch")
                
                # Return a more user-friendly message about the CAPTCHA
                return {
                    "error": "Search engines are currently requiring CAPTCHA verification. Unable to retrieve web information.",
                    "type": "web_information",
                    "query": search_query
                }
            
            # Google search results are typically in divs with class 'g'
            search_results = []
            result_divs = soup.select('div.g')
            
            if not result_divs:
                # Try alternative selectors
                result_divs = soup.select('[data-hveid]')
                log_with_route(logging.DEBUG, f"Found {len(result_divs)} results with alternative selector", source_type="WebSearch")
            
            for result in result_divs:
                # Find heading element which contains the title and link
                heading = result.select_one('h3')
                if not heading:
                    continue
                    
                # For Google, the link is usually in an <a> tag that's a parent or sibling of the h3
                link_elem = result.select_one('a')
                snippet_elem = result.select_one('.VwiC3b') or result.select_one('.st')
                
                if heading and link_elem:
                    title = heading.get_text(strip=True)
                    link = link_elem.get('href')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Clean up Google links which often have tracking parameters
                    if link.startswith('/url?') or link.startswith('/search?'):
                        params = link.split('?', 1)[1].split('&')
                        for param in params:
                            if param.startswith('q='):
                                link = param[2:]
                                break
                    
                    # Decode URL if needed
                    from urllib.parse import unquote
                    link = unquote(link)
                    
                    # Only include results with meaningful content
                    if title and link and link.startswith(('http://', 'https://')) and snippet:
                        search_results.append({
                            'title': title,
                            'url': link,
                            'snippet': snippet
                        })
                        log_with_route(logging.DEBUG, f"Added result: {title}", source_type="WebSearch")
                
                # Limit to max 5 results
                if len(search_results) >= 5:
                    break
            
            # If no results found with direct selectors, try a broader approach
            if not search_results:
                log_with_route(logging.WARNING, "No direct results found, trying broader selectors", source_type="WebSearch")
                
                # Look for any links with substantial text near them
                for link in soup.find_all('a'):
                    href = link.get('href')
                    if not href or not href.startswith(('http://', 'https://')) or 'google' in href:
                        continue
                        
                    title = link.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue
                    
                    # Look for nearby text that could be a snippet
                    parent = link.parent
                    siblings = list(parent.next_siblings) + list(parent.previous_siblings)
                    
                    snippet = ""
                    for sibling in siblings:
                        if hasattr(sibling, 'get_text'):
                            text = sibling.get_text(strip=True)
                            if len(text) > 30:
                                snippet = text
                                break
                    
                    if not snippet:
                        # Try looking in parent's parent
                        if parent.parent:
                            for elem in parent.parent.find_all(['p', 'div', 'span']):
                                if elem != parent and elem != link:
                                    text = elem.get_text(strip=True)
                                    if len(text) > 30:
                                        snippet = text
                                        break
                    
                    if snippet:
                        search_results.append({
                            'title': title,
                            'url': href,
                            'snippet': snippet
                        })
                        log_with_route(logging.DEBUG, f"Added fallback result: {title}", source_type="WebSearch")
                    
                    if len(search_results) >= 3:
                        break
            
            # Return no results message if nothing found
            if not search_results:
                log_with_route(logging.WARNING, "No search results found after all attempts", source_type="WebSearch")
                return {
                    "error": "No relevant information found for your query.",
                    "type": "web_information",
                    "query": search_query
                }
            
            # Create a summary from the results
            summary = f"Information about '{search_query}':\n\n"
            for result in search_results[:3]:
                summary += f"• {result['title']}: {result['snippet'][:150]}...\n\n"
            
            # Prepare the final result
            result = {
                "type": "web_information",
                "query": search_query,
                "summary": summary,
                "sources": [{'title': r['title'], 'url': r['url']} for r in search_results],
                "fetched_at": current_time
            }
            
            # Cache the result
            self._web_cache[cache_key] = {
                'data': result,
                'timestamp': current_time
            }
            
            log_with_route(logging.INFO, f"Successfully processed web search with {len(search_results)} results", source_type="WebSearch")
            return result
            
        except Exception as e:
            error_trace = traceback.format_exc()
            log_with_route(logging.ERROR, f"Error retrieving web information: {str(e)}", 
                        source_type="WebSearch", exc_info=True)
            
            # Return a more user-friendly error message
            return {
                "error": "Unable to retrieve information from the web at this time.",
                "details": str(e),
                "type": "web_information",
                "query": search_query
            }
            
    def _extract_web_content(self, url: str, query: str) -> str:
        """Extract main content from a web page relevant to query"""
        try:
            # Set a timeout to prevent hanging on slow websites
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
                element.decompose()
            
            # Find main content areas - prioritize article or main tags
            main_content = soup.find('article') or soup.find('main') or soup.find('div', class_='content') or soup.body
            
            if main_content:
                # Get all paragraphs from main content
                paragraphs = main_content.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
                
                # If no substantial paragraphs found, get the main text
                if not content:
                    content = main_content.get_text(strip=True)
                    content = ' '.join(content.split())  # Normalize whitespace
            else:
                # Fallback to the body content
                content = soup.body.get_text(strip=True) if soup.body else ""
                content = ' '.join(content.split())
            
            # Extract relevant sections based on the query terms
            # This is a simple relevance filter - can be improved with NLP
            query_terms = set(query.lower().split())
            paragraphs = content.split('. ')
            
            # Score paragraphs by relevance to query
            scored_paragraphs = []
            for para in paragraphs:
                if len(para) < 30:  # Skip very short phrases
                    continue
                    
                para_terms = set(para.lower().split())
                relevance = len(para_terms.intersection(query_terms))
                scored_paragraphs.append((para, relevance))
            
            # Sort by relevance score (descending)
            scored_paragraphs.sort(key=lambda x: x[1], reverse=True)
            
            # Get the most relevant content (up to 8000 chars to allow for better AI summarization)
            relevant_content = ". ".join([p[0] for p in scored_paragraphs[:15]])
            if len(relevant_content) > 8000:
                relevant_content = relevant_content[:8000] + "..."
                
            return relevant_content
            
        except Exception as e:
            logging.warning(f"Error extracting content from {url}: {str(e)}")
            return ""
    
    def _summarize_web_content_with_ai(self, query: str, results: List[Dict]) -> str:
        """Summarize web content using AI"""
        try:
            if not results:
                return "No relevant information found for your query."
            
            # Prepare the content for AI summarization
            formatted_content = f"Information about: {query}\n\n"
            
            for i, result in enumerate(results, 1):
                # Add source information and snippets
                formatted_content += f"SOURCE {i}: {result['title']} ({result['url']})\n"
                formatted_content += f"SNIPPET: {result['snippet']}\n"
                
                # Add a portion of the full content
                content_preview = result['content'][:2500] + "..." if len(result['content']) > 2500 else result['content']
                formatted_content += f"CONTENT: {content_preview}\n\n"
            
            # Create a prompt for the LLM to summarize the content
            summarization_prompt = f"""
            You are an AI research assistant. Your task is to summarize the following information 
            retrieved from the web about: "{query}"
            
            Provide a comprehensive summary that:
            1. Directly answers the query with factual information
            2. Synthesizes information from all sources
            3. Highlights any contradictions or disagreements between sources
            4. Cites the sources when stating key facts (use [Source 1], [Source 2], etc.)
            5. Is well-structured and easy to understand
            6. Distinguishes between factual information and any opinions present in the sources
            
            Here is the web content to summarize:
            
            {formatted_content}
            
            Summary:
            """
            
            # Use LangChain directly instead of importing get_ai_response
            from langchain_openai import AzureChatOpenAI
            
            llm = AzureChatOpenAI(
                openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
                azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
                azure_deployment="wegweiser",
                openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
            )
            
            response = llm.invoke(summarization_prompt)
            return response.content
            
        except Exception as e:
            logging.error(f"Error summarizing web content: {str(e)}", exc_info=True)
            
            # Fallback to basic summary if AI summarization fails
            fallback_summary = f"Information found for query '{query}':\n\n"
            for i, result in enumerate(results, 1):
                fallback_summary += f"Source {i}: {result['title']}\n"
                fallback_summary += f"URL: {result['url']}\n"
                fallback_summary += f"Excerpt: {result['snippet']}\n\n"
            
            fallback_summary += "(An error occurred during AI summarization. This is a basic summary of the search results.)"
            return fallback_summary
