# Filepath: app/utilities/ollama_analysis.py
# ollama_analysis.py
from llama_index.llms.ollama import Ollama
import re
from app.utilities.loggings import logger
import tiktoken

# Global variable to track total token usage
total_tokens_used = 0

def count_tokens(text):
    """Count the number of tokens in the given text."""
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")  # Using GPT-3.5 encoding as an approximation
    return len(enc.encode(text))

def analyze_logs_with_ollama(grouped_logs, model="qwen2.5:latest", request_timeout=600.0):
    global total_tokens_used
    logger.info("Starting daily log analysis with Ollama.")
    ollama_model = Ollama(
        model=model,
        base_url="http://zeus.wegweiser.tech:11434",
        request_timeout=request_timeout
    )
    daily_analyses = {}
    daily_health_scores = {}

    for date, logs in grouped_logs.items():
        important_messages = extract_important_log_messages(logs)
        
        if not important_messages:
            logger.info(f"No important messages found for {date}")
            daily_analyses[date] = "No significant errors, warnings, critical events, or audit failures found."
            daily_health_scores[date] = 100
            continue

        log_text = "\n".join(important_messages[:100])  # Limit to first 100 important messages

        prompt = create_prompt(date, log_text)
        prompt_tokens = count_tokens(prompt)
        total_tokens_used += prompt_tokens
        logger.info(f"Analyzing logs for {date} (Prompt tokens: {prompt_tokens})")

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = ollama_model.complete(prompt)
                daily_analyses[date] = response.text
                response_tokens = count_tokens(response.text)
                total_tokens_used += response_tokens
                logger.info(f"Ollama response for {date} (Response tokens: {response_tokens}):\n{response.text}")
                
                health_score = extract_health_score(response.text)
                if health_score is not None:
                    daily_health_scores[date] = health_score
                    logger.info(f"Health score for {date}: {health_score}")
                    break
                else:
                    if attempt < max_attempts - 1:
                        logger.warning(f"No health score found in attempt {attempt + 1}. Retrying...")
                        prompt += "\n\nYou did not provide a health score. Please analyze the logs again and ensure you provide a health score between 1 and 100."
                    else:
                        logger.error(f"Failed to get health score after {max_attempts} attempts. Using default score of 50.")
                        daily_health_scores[date] = 50
            except Exception as e:
                logger.error(f"Error calling Ollama API for {date} (Attempt {attempt + 1}): {e}")
                if attempt == max_attempts - 1:
                    daily_analyses[date] = f"Failed to analyze logs: {str(e)}"
                    daily_health_scores[date] = 50  # Use 50 as default for errors

    logger.info(f"Total tokens used for Ollama analysis: {total_tokens_used}")
    return daily_analyses, daily_health_scores

def create_prompt(date, log_text):
    prompt = f"""Analyze these important Windows event log entries for {date}, focusing on errors, warnings, critical events, and audit failures. Provide a summary covering:
    1. Identify the most critical or frequent events and their implications for system stability and security.
    2. Assess the overall health of the system based on these events.
    3. Highlight any recurring errors, warnings, or suspicious activities.
    4. Provide 2-3 key actionable recommendations to improve system health and security.

    Structure your response in basic HTML format with tags such as <p>, <ul>, <li>, and <br> to ensure readability:
    - Brief summary of key findings (2-3 sentences)
    - Analysis of critical events (3-5 bullet points)
    - Overall system health assessment (1-2 sentences)
    - Recommendations (2-3 bullet points)

    You MUST assign a health score from 1 to 100, where:
      100-90: Excellent health, no significant issues
      89-70: Good health, minor issues present
      69-50: Fair health, some concerns that need attention
      49-30: Poor health, significant issues present
      29-1: Critical condition, immediate attention required

    Format the score as 'Health Score: X' where X is the numeric score.
    The score should reflect the overall system health, not just the presence of errors. A few errors in a largely stable system should not result in an extremely low score.

    IMPORTANT: You must provide a health score in your response. Failure to do so will result in an error.

    Logs:
    {log_text}

    Analysis:
    """
    return prompt

def extract_health_score(text):
    """Extract health score from Ollama response."""
    try:
        match = re.search(r'Health Score:\s*(\d+)', text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            logger.info(f"Health score found: {score}")
            return min(max(score, 1), 100)  # Ensure score is between 1 and 100
        else:
            logger.warning("No health score found in Ollama's response.")
            return None
    except Exception as e:
        logger.error(f"Error extracting health score: {e}")
        return None

def calculate_overall_health_score(daily_scores):
    """Calculate overall health score from daily scores."""
    if not daily_scores:
        return 50  # Default to midpoint if no scores

    overall_score = sum(daily_scores.values()) / len(daily_scores)
    
    logger.info(f"Raw overall health score: {overall_score}")
    if overall_score < 10:
        logger.warning("Unusually low overall health score detected. This might indicate an issue with score calculation or an extremely problematic system state.")
    
    return max(min(round(overall_score), 100), 1)  # Ensure the score is between 1 and 100

def extract_important_log_messages(logs):
    """Extract important log messages, including errors, warnings, critical events, and audit events."""
    important_messages = []
    log_types_count = {"INFORMATION": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0, "AUDIT SUCCESS": 0, "AUDIT FAILURE": 0}

    for log in logs:
        message = log.get('message', '').strip()
        level = log.get('eventtype', '').upper()
        event_id = log.get('eventid', '')
        source_name = log.get('sourcename', '')
        
        log_types_count[level] = log_types_count.get(level, 0) + 1

        if level in ['ERROR', 'WARNING', 'CRITICAL'] or any(keyword in message.lower() for keyword in ['error', 'warning', 'critical', 'failure', 'failed']):
            important_messages.append(f"EventID {event_id} - {level} - {source_name}: {message}")
    
    return important_messages