from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging
import time
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from flask import current_app

class QueryType(Enum):
    FACTUAL = "factual"       # Looking for specific facts
    EXPLORATORY = "exploratory"  # Learning about a topic
    COMPARATIVE = "comparative"  # Comparing multiple things
    PROCEDURAL = "procedural"    # How to do something
    CURRENT_EVENTS = "current_events"  # Recent developments
    TECHNICAL = "technical"    # Technical/specialized information

class Source(BaseModel):
    """Information source with metadata"""
    title: str
    url: str
    content: str
    snippet: str = ""
    credibility_score: float = 0.0
    relevance_score: float = 0.0
    fetched_at: int = Field(default_factory=lambda: int(time.time()))

class SearchTool(BaseModel):
    """Tool for searching a specific data source"""
    name: str
    description: str
    requires_api_key: bool = False
    api_key_config_name: Optional[str] = None
    search_url_template: Optional[str] = None
    
    def search(self, query: str) -> List[Dict]:
        """Implementation should be provided by subclasses"""
        pass

class Reflection(BaseModel):
    """Agent's reflection on process and results"""
    information_gaps: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    reasoning: str = ""
    next_steps: List[str] = Field(default_factory=list)

class AgentMemory(BaseModel):
    """Agent's memory of completed actions and results"""
    search_history: List[Dict] = Field(default_factory=list)
    visited_urls: List[str] = Field(default_factory=list)
    failed_attempts: List[Dict] = Field(default_factory=list)
    query_refinements: List[str] = Field(default_factory=list)
    current_task_tree: Dict = Field(default_factory=dict)
    
    def add_search(self, query: str, source: str, results_count: int, timestamp: int = None):
        if timestamp is None:
            timestamp = int(time.time())
        self.search_history.append({"query": query, "source": source, 
                                  "results_count": results_count, "timestamp": timestamp})
    
    def add_visited_url(self, url: str):
        if url not in self.visited_urls:
            self.visited_urls.append(url)
    
    def add_failure(self, action: str, reason: str):
        self.failed_attempts.append({"action": action, "reason": reason, 
                                   "timestamp": int(time.time())})
    
    def has_visited(self, url: str) -> bool:
        return url in self.visited_urls

class WebRetrievalAgent:
    """Autonomous web information retrieval agent"""
    
    def __init__(self, llm=None):
        self.tools = self._initialize_tools()
        self.memory = AgentMemory()
        self.max_iterations = 5
        self.current_iteration = 0
        self.sources = []
        self.llm = llm or self._initialize_llm()
        
    def _initialize_llm(self):
        """Initialize the LLM for agent reasoning"""
        try:
            return AzureChatOpenAI(
                openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
                azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
                azure_deployment="wegweiser",
                openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
                temperature=0.0  # Lower temperature for more deterministic reasoning
            )
        except Exception as e:
            logging.error(f"Failed to initialize LLM: {str(e)}")
            raise

    def _initialize_tools(self) -> Dict[str, SearchTool]:
        """Initialize available search tools"""
        return {
            "web_search": DuckDuckGoSearchTool(),
            "news_search": NewsSearchTool(),
            "wikipedia": WikipediaSearchTool(),
            "scholarly": ScholarlySearchTool(),
            "technical_docs": TechnicalDocsSearchTool(),
        }
    
    def retrieve_information(self, query: str, max_sources: int = 5) -> Dict:
        """Main entry point for information retrieval"""
        self._reset_state()
        
        # First, analyze the query to determine the best approach
        query_analysis = self._analyze_query(query)
        query_type = query_analysis["query_type"]
        logging.info(f"Query analysis: {query_type} - {query}")
        
        # Create a task plan based on query analysis
        task_plan = self._create_task_plan(query, query_analysis)
        self.memory.current_task_tree = task_plan
        
        # Execute the information retrieval plan
        while self.current_iteration < self.max_iterations and task_plan["subtasks"]:
            self.current_iteration += 1
            current_task = task_plan["subtasks"].pop(0)
            
            # Execute the current task
            task_result = self._execute_task(current_task)
            
            # Update the task plan based on results
            new_tasks = self._update_plan(task_plan, current_task, task_result)
            task_plan["subtasks"].extend(new_tasks)
            
            # Stop if we have enough high-quality sources
            if len(self.sources) >= max_sources and self._overall_confidence() > 0.8:
                break
        
        # Synthesize the final result
        final_result = self._synthesize_results(query, query_type)
        
        # Perform final reflection
        reflection = self._reflect_on_results(query, final_result)
        
        return {
            "query": query,
            "query_type": query_type,
            "summary": final_result,
            "sources": [{"title": s.title, "url": s.url} for s in self.sources],
            "confidence": reflection.confidence_score,
            "information_gaps": reflection.information_gaps,
            "contradictions": reflection.contradictions,
            "agent_reflections": reflection.reasoning
        }
    
    def _reset_state(self):
        """Reset the agent state for a new query"""
        self.current_iteration = 0
        self.sources = []
        # Keep memory across queries but clear task-specific info
        self.memory.current_task_tree = {}
        self.memory.query_refinements = []
    
    def _analyze_query(self, query: str) -> Dict:
        """Analyze the query to determine type and strategy"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert query analyzer. Analyze the given query and classify it into one of these types:
                        - factual: Looking for specific facts
                        - exploratory: Learning about a topic in general
                        - comparative: Comparing multiple things
                        - procedural: How to do something
                        - current_events: Recent news or developments
                        - technical: Technical or specialized information
                        
                        Also identify:
                        1. Key entities that need to be researched
                        2. Potential subtopics to explore
                        3. If it needs current information or historical is sufficient
                        4. The level of technical depth required (basic/advanced)
                        
                        Format response as JSON with keys: query_type, entities, subtopics, needs_current, technical_depth.
                        """),
            ("human", "{query}")
        ])
        
        response = self.llm.invoke(prompt.format(query=query))
        
        try:
            analysis = json.loads(response.content)
            return analysis
        except Exception:
            # Fallback if parsing fails
            return {
                "query_type": "factual",
                "entities": [query],
                "subtopics": [],
                "needs_current": True,
                "technical_depth": "basic"
            }
    
    def _create_task_plan(self, query: str, query_analysis: Dict) -> Dict:
        """Create a decomposed plan of tasks for information retrieval"""
        query_type = query_analysis["query_type"]
        entities = query_analysis["entities"]
        
        task_plan = {
            "main_query": query,
            "subtasks": []
        }
        
        # Initial search task
        task_plan["subtasks"].append({
            "type": "search",
            "query": query,
            "tool": self._select_tool_for_query_type(query_type),
            "priority": 1
        })
        
        # Add entity-specific searches if needed
        for entity in entities:
            if entity.lower() not in query.lower():
                task_plan["subtasks"].append({
                    "type": "search",
                    "query": f"{entity} {query}",
                    "tool": "web_search",
                    "priority": 2
                })
        
        # For current events, add a news-specific task
        if query_analysis["needs_current"]:
            task_plan["subtasks"].append({
                "type": "search",
                "query": f"latest {query}",
                "tool": "news_search",
                "priority": 1 if query_type == "current_events" else 3
            })
        
        # For technical queries, add technical docs search
        if query_analysis["technical_depth"] == "advanced":
            task_plan["subtasks"].append({
                "type": "search",
                "query": query,
                "tool": "technical_docs",
                "priority": 2
            })
        
        # Sort tasks by priority
        task_plan["subtasks"] = sorted(task_plan["subtasks"], key=lambda x: x["priority"])
        
        return task_plan
    
    def _select_tool_for_query_type(self, query_type: str) -> str:
        """Select the most appropriate search tool based on query type"""
        tool_mapping = {
            "factual": "web_search",
            "exploratory": "web_search",
            "comparative": "web_search",
            "procedural": "web_search",
            "current_events": "news_search",
            "technical": "technical_docs"
        }
        return tool_mapping.get(query_type, "web_search")
    
    def _execute_task(self, task: Dict) -> Dict:
        """Execute a single task in the plan"""
        task_type = task["type"]
        
        if task_type == "search":
            return self._execute_search_task(task)
        elif task_type == "extract":
            return self._execute_extract_task(task)
        elif task_type == "verify":
            return self._execute_verification_task(task)
        else:
            return {"success": False, "reason": f"Unknown task type: {task_type}"}
    
    def _execute_search_task(self, task: Dict) -> Dict:
        """Execute a search task using the specified tool"""
        query = task["query"]
        tool_name = task["tool"]
        
        if tool_name not in self.tools:
            self.memory.add_failure(f"search_{tool_name}", "Tool not available")
            return {"success": False, "reason": f"Tool {tool_name} not available"}
        
        try:
            # Execute the search
            tool = self.tools[tool_name]
            search_results = tool.search(query)
            
            # Record in memory
            self.memory.add_search(query, tool_name, len(search_results))
            
            # Process results
            new_sources = self._process_search_results(search_results, query)
            
            return {
                "success": True,
                "sources_added": len(new_sources),
                "sources_found": len(search_results)
            }
        except Exception as e:
            self.memory.add_failure(f"search_{tool_name}", str(e))
            logging.error(f"Error executing search task: {str(e)}")
            return {"success": False, "reason": str(e)}
    
    def _process_search_results(self, results: List[Dict], query: str) -> List[Source]:
        """Process and filter search results"""
        new_sources = []
        
        for result in results[:5]:  # Limit to top 5 results
            # Skip already visited URLs
            if self.memory.has_visited(result["url"]):
                continue
                
            try:
                # Extract content
                content = self._extract_content_from_url(result["url"], query)
                if not content:
                    continue
                
                # Create source object
                source = Source(
                    title=result["title"],
                    url=result["url"],
                    content=content,
                    snippet=result.get("snippet", ""),
                )
                
                # Evaluate source quality
                source = self._evaluate_source(source, query)
                
                # Add if it's relevant
                if source.relevance_score > 0.3:
                    new_sources.append(source)
                    self.sources.append(source)
                
                # Mark as visited
                self.memory.add_visited_url(result["url"])
                
            except Exception as e:
                logging.warning(f"Error processing result {result['url']}: {str(e)}")
        
        return new_sources
    
    def _extract_content_from_url(self, url: str, query: str) -> str:
        """Extract relevant content from a URL"""
        try:
            # Fetch the content
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Find main content
            main_content = soup.find('article') or soup.find('main') or soup.body
            
            # Extract paragraphs
            if main_content:
                paragraphs = main_content.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs 
                                 if len(p.get_text(strip=True)) > 50])
            else:
                content = soup.get_text(strip=True)
            
            # Find most relevant sections
            return self._extract_relevant_sections(content, query)
            
        except Exception as e:
            logging.warning(f"Error extracting content from {url}: {str(e)}")
            return ""
    
    def _extract_relevant_sections(self, text: str, query: str) -> str:
        """Extract sections most relevant to the query"""
        # Split into chunks
        chunks = text.split('. ')
        
        # Score chunks by relevance
        query_terms = set(query.lower().split())
        scored_chunks = []
        
        for chunk in chunks:
            if len(chunk) < 30:
                continue
            
            chunk_terms = set(chunk.lower().split())
            relevance = len(chunk_terms.intersection(query_terms))
            scored_chunks.append((chunk, relevance))
        
        # Sort by relevance and take top chunks
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        relevant_chunks = [c[0] for c in scored_chunks[:15]]
        
        return '. '.join(relevant_chunks)
    
    def _evaluate_source(self, source: Source, query: str) -> Source:
        """Evaluate source relevance and credibility"""
        # Analyze domain for credibility
        domain = urlparse(source.url).netloc
        
        # Basic credibility signals
        credibility_score = 0.5  # Default middle score
        if any(d in domain for d in ['.gov', '.edu', 'wikipedia.org']):
            credibility_score = 0.9
        elif any(d in domain for d in ['medium.com', 'wordpress', 'blogspot']):
            credibility_score = 0.4
        
        # Calculate relevance based on content
        query_terms = query.lower().split()
        content_words = source.content.lower().split()
        
        # Simple TF score for query terms
        term_frequency = 0
        for term in query_terms:
            term_frequency += content_words.count(term)
        
        if content_words:
            relevance_score = min(1.0, term_frequency / len(content_words) * 20)
        else:
            relevance_score = 0.0
        
        # Update source scores
        source.credibility_score = credibility_score
        source.relevance_score = relevance_score
        
        return source
    
    def _update_plan(self, task_plan: Dict, completed_task: Dict, task_result: Dict) -> List[Dict]:
        """Update the task plan based on task results"""
        new_tasks = []
        
        # If search was successful, add extraction tasks
        if completed_task["type"] == "search" and task_result.get("success", False):
            # If not enough good sources, try to refine the query
            if task_result["sources_added"] == 0 and self.memory.query_refinements:
                refined_query = self._refine_query(completed_task["query"])
                if refined_query:
                    new_tasks.append({
                        "type": "search",
                        "query": refined_query,
                        "tool": completed_task["tool"],
                        "priority": completed_task["priority"] + 0.5
                    })
                    self.memory.query_refinements.append(refined_query)
        
        # If we need verification due to contradictions
        if self._has_contradictions():
            new_tasks.append({
                "type": "verify",
                "topic": self._identify_contradiction_topic(),
                "priority": 0.5  # High priority
            })
        
        return new_tasks
    
    def _refine_query(self, original_query: str) -> str:
        """Refine a query based on previous results"""
        # Use the LLM to refine the query
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a search query refinement expert. 
                      I've searched for the following query but didn't get useful results:
                      "{query}"
                      
                      Please rewrite this query to make it more likely to find relevant information.
                      Use more specific terms, alternative phrasings, or add context.
                      Return only the refined query text with no explanation."""),
            ("human", "{query}")
        ])
        
        response = self.llm.invoke(prompt.format(query=original_query))
        return response.content.strip()
    
    def _has_contradictions(self) -> bool:
        """Check if current sources have contradicting information"""
        # Simple version - just check if we have enough sources to potentially have contradictions
        return len(self.sources) >= 3
    
    def _identify_contradiction_topic(self) -> str:
        """Identify the topic with contradictory information"""
        # In a real implementation, this would analyze source content to find contradictions
        return "main topic"  # Simplified version
    
    def _overall_confidence(self) -> float:
        """Calculate overall confidence in the results"""
        if not self.sources:
            return 0.0
        
        # Average relevance and credibility
        avg_relevance = sum(s.relevance_score for s in self.sources) / len(self.sources)
        avg_credibility = sum(s.credibility_score for s in self.sources) / len(self.sources)
        
        # Weight relevance more heavily than credibility
        confidence = (avg_relevance * 0.7) + (avg_credibility * 0.3)
        
        # Adjust confidence based on number of sources
        source_count_factor = min(1.0, len(self.sources) / 5)
        
        return confidence * source_count_factor
    
    def _synthesize_results(self, query: str, query_type: str) -> str:
        """Synthesize results into a coherent response"""
        if not self.sources:
            return "I couldn't find relevant information for your query."
        
        # Prepare source content for the LLM
        source_content = ""
        for i, source in enumerate(self.sources, 1):
            source_content += f"Source {i}: {source.title}\n"
            source_content += f"URL: {source.url}\n"
            source_content += f"Content: {source.content[:1000]}...\n\n"
        
        # Create synthesis prompt
        system_message = """You are an expert research synthesizer. Based on the following sources, 
                        create a comprehensive response to the query. Include relevant facts from the sources 
                        and cite them as [Source X] where appropriate. Ensure your synthesis is well-structured,
                        objective, and directly addresses the query."""
                        
        if query_type == QueryType.COMPARATIVE.value:
            system_message += "\nFor this comparative query, make sure to highlight differences and similarities."
        elif query_type == QueryType.PROCEDURAL.value:
            system_message += "\nFor this procedural query, prioritize clear step-by-step instructions."
        elif query_type == QueryType.CURRENT_EVENTS.value:
            system_message += "\nFor this current events query, prioritize the most recent information and note dates when available."
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", f"Query: {query}\n\nSources:\n{source_content}")
        ])
        
        # Get synthesis from LLM
        response = self.llm.invoke(prompt)
        return response.content
    
    def _reflect_on_results(self, query: str, result: str) -> Reflection:
        """Reflect on the quality and completeness of results"""
        # Create reflection prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a critical research evaluator. Analyze the following query and the synthesized response. 
                       Identify any gaps in information, contradictions, or areas where more research is needed. 
                       Also evaluate the overall confidence we should have in this response.
                       
                       Format your response as JSON with these keys:
                       - information_gaps: list of specific topics needing more information
                       - contradictions: list of contradictory points found
                       - confidence_score: float between 0-1
                       - reasoning: detailed explanation for your evaluation
                       - next_steps: list of recommended follow-up research actions"""),
            ("human", f"Query: {query}\n\nSynthesized Response: {result}")
        ])
        
        response = self.llm.invoke(prompt)
        
        try:
            reflection_data = json.loads(response.content)
            return Reflection(**reflection_data)
        except Exception:
            # Fallback reflection if parsing fails
            return Reflection(
                information_gaps=["Could not analyze information gaps"],
                confidence_score=self._overall_confidence(),
                reasoning="Failed to generate structured reflection",
                next_steps=["Retry with more specific query"]
            )


# Example search tool implementations (stubs)
class DuckDuckGoSearchTool(SearchTool):
    """Search tool using DuckDuckGo"""
    
    def __init__(self):
        super().__init__(
            name="DuckDuckGo Search",
            description="Search the web using DuckDuckGo",
            requires_api_key=False,
        )
    
    def search(self, query: str) -> List[Dict]:
        """Execute search query"""
        results = []
        try:
            search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for result in soup.select('.result'):
                title_elem = result.select_one('.result__title')
                snippet_elem = result.select_one('.result__snippet')
                link_elem = result.select_one('.result__url')
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link_a = title_elem.find('a')
                    link = link_a.get('href') if link_a else link_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append({
                        'title': title,
                        'url': link,
                        'snippet': snippet
                    })
            
            return results[:10]  # Return top 10 results
            
        except Exception as e:
            logging.error(f"DuckDuckGo search error: {str(e)}")
            return []

# Stub implementations for other search tools
class NewsSearchTool(SearchTool):
    def __init__(self):
        super().__init__(name="News Search", description="Search for news articles")
    
    def search(self, query: str) -> List[Dict]:
        # Stub implementation
        return []

class WikipediaSearchTool(SearchTool):
    def __init__(self):
        super().__init__(name="Wikipedia", description="Search Wikipedia articles")
    
    def search(self, query: str) -> List[Dict]:
        # Stub implementation
        return []

class ScholarlySearchTool(SearchTool):
    def __init__(self):
        super().__init__(name="Scholarly Search", description="Search academic papers")
    
    def search(self, query: str) -> List[Dict]:
        # Stub implementation
        return []

class TechnicalDocsSearchTool(SearchTool):
    def __init__(self):
        super().__init__(name="Technical Docs", description="Search technical documentation")
    
    def search(self, query: str) -> List[Dict]:
        # Stub implementation
        return []


# Example usage
def retrieve_web_information(query: str, llm=None) -> Dict:
    """Function to get information from the web using the WebRetrievalAgent"""
    agent = WebRetrievalAgent(llm)
    return agent.retrieve_information(query)
