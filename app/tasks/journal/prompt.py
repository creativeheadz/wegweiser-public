# Filepath: app/tasks/journal/prompt.py
JOURNAL_PROMPT = """
Analyze the following Linux Journal events and provide a comprehensive system journal analysis report. Your analysis should include:

1. Detailed examination of systemd journal entries, including service status changes, boot sequences, and system state transitions.
2. Identification of critical system events, errors, and warnings that could impact system stability, performance, or security.
3. Analysis of service dependencies, startup failures, and daemon health indicators visible in journal logs.
4. Assessment of system resource utilization patterns, memory pressure indicators, and performance bottlenecks reflected in journal entries.
5. Evaluation of security-related events, including authentication attempts, privilege changes, and potential security incidents.
6. Analysis of hardware-related events, driver issues, and kernel messages that could indicate hardware problems or compatibility issues.
7. Assessment of system maintenance events, including package updates, configuration changes, and scheduled tasks.
8. Comprehensive recommendations for system optimization, monitoring enhancements, and proactive maintenance strategies.

Structure your response in basic HTML format using tags like <p>, <ul>, <li>, and <br> to ensure readability:
- Summary of journal analysis and key system health findings (2-3 sentences)
- Detailed analysis of critical system events and service health (4-6 bullet points)
- Security and authentication event assessment (2-3 bullet points)
- Hardware and kernel-level event analysis (2-3 bullet points)
- System performance and resource utilization insights (2-3 sentences)
- Proactive monitoring and maintenance recommendations for MSP implementation (3-4 bullet points)
- Long-term system health and optimization suggestions (1-2 sentences)

- Declare a healthscore based on these findings between 1 and 100 where 100 is a problem-free state.

Journal Data:
{journal_data}
"""
