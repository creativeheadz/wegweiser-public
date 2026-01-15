#!/usr/bin/env python3
"""
Analyze Registration Attempts - Security Analysis Tool
Analyzes registration attempts from logs to identify bots vs legitimate users
"""

import re
import json
from datetime import datetime
from collections import defaultdict

def analyze_user_agent(ua_string, platform_header):
    """Analyze user agent for bot indicators"""
    indicators = []
    
    if not ua_string or ua_string == 'Unknown':
        indicators.append('MISSING_UA')
        return indicators
    
    ua_lower = ua_string.lower()
    
    # OS Mismatch Detection
    if platform_header:
        platform_lower = platform_header.lower()
        
        # Windows mismatch
        if 'windows' in ua_lower and platform_lower not in ['windows', '']:
            indicators.append(f'OS_MISMATCH(UA:Windows,Header:{platform_header})')
        # Mac mismatch
        elif ('mac' in ua_lower or 'macintosh' in ua_lower) and platform_lower not in ['macos', 'mac', '']:
            indicators.append(f'OS_MISMATCH(UA:Mac,Header:{platform_header})')
        # Linux mismatch
        elif 'linux' in ua_lower and platform_lower not in ['linux', '']:
            indicators.append(f'OS_MISMATCH(UA:Linux,Header:{platform_header})')
    
    # Known bot patterns
    bot_patterns = [
        ('zgrab', 'ZGRAB_SCANNER'),
        ('bot', 'BOT_UA'),
        ('crawler', 'CRAWLER'),
        ('spider', 'SPIDER'),
        ('scraper', 'SCRAPER'),
        ('headless', 'HEADLESS_BROWSER'),
        ('phantom', 'PHANTOM_JS'),
        ('selenium', 'SELENIUM'),
        ('puppeteer', 'PUPPETEER')
    ]
    
    for pattern, label in bot_patterns:
        if pattern in ua_lower:
            indicators.append(label)
    
    # Outdated browser versions (common in bots)
    if 'msie' in ua_lower or 'internet explorer' in ua_lower:
        indicators.append('OUTDATED_BROWSER(IE)')
    
    return indicators


def parse_registration_log_line(line):
    """Parse a registration attempt log line"""
    
    # Extract timestamp
    timestamp_match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
    if not timestamp_match:
        return None
    
    timestamp = timestamp_match.group(1)
    
    # Extract IP
    ip_match = re.search(r'PID: \d+, ([\d.]+)', line)
    ip = ip_match.group(1) if ip_match else 'unknown'
    
    # Extract reCAPTCHA score
    score_match = re.search(r'score=([0-9.]+)', line)
    score = float(score_match.group(1)) if score_match else None
    
    # Extract user agent
    ua_match = re.search(r'User-Agent: ([^-]+?) -', line)
    user_agent = ua_match.group(1).strip().strip('"') if ua_match else 'Unknown'
    
    # Extract platform from headers
    platform_match = re.search(r"'Sec-Ch-Ua-Platform': '?\"?([^'\"]+)", line)
    platform = platform_match.group(1) if platform_match else ''
    
    # Check if blocked
    is_blocked = 'reCAPTCHA failed' in line or 'Registration blocked' in line
    
    return {
        'timestamp': timestamp,
        'ip': ip,
        'score': score,
        'user_agent': user_agent,
        'platform': platform,
        'is_blocked': is_blocked,
        'raw_line': line
    }


def analyze_log_file(log_path='/opt/wegweiser/wlog/wegweiser.log'):
    """Analyze registration attempts from log file"""
    
    print("\n" + "="*80)
    print("REGISTRATION ATTEMPT ANALYSIS")
    print("="*80 + "\n")
    
    attempts = []
    
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if '/register' in line and 'POST' in line and ('reCAPTCHA' in line or 'Registration' in line):
                    parsed = parse_registration_log_line(line)
                    if parsed:
                        attempts.append(parsed)
    except FileNotFoundError:
        print(f"❌ Log file not found: {log_path}")
        return
    
    if not attempts:
        print("No registration attempts found in log file.")
        return
    
    print(f"Found {len(attempts)} registration attempts\n")
    print("-" * 80)
    
    # Group by IP
    by_ip = defaultdict(list)
    for attempt in attempts:
        by_ip[attempt['ip']].append(attempt)
    
    # Analyze each unique IP
    for ip, ip_attempts in sorted(by_ip.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n📍 IP Address: {ip} ({len(ip_attempts)} attempts)")
        print("-" * 80)
        
        # Calculate average score
        scores = [a['score'] for a in ip_attempts if a['score'] is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Analyze bot indicators
        first_attempt = ip_attempts[0]
        bot_indicators = analyze_user_agent(first_attempt['user_agent'], first_attempt['platform'])
        
        # Determine legitimacy
        is_bot = False
        reasons = []
        
        if avg_score < 0.3:
            is_bot = True
            reasons.append(f"Low reCAPTCHA score (avg: {avg_score:.2f})")
        
        if bot_indicators:
            is_bot = True
            reasons.append(f"Bot indicators: {', '.join(bot_indicators)}")
        
        if len(ip_attempts) > 3:
            is_bot = True
            reasons.append(f"Multiple attempts ({len(ip_attempts)})")
        
        # Print assessment
        if is_bot:
            print(f"  🤖 ASSESSMENT: Likely BOT")
            print(f"  📊 Confidence: {min(99, int((1 - avg_score) * 100 + len(bot_indicators) * 20))}%")
            print(f"  🚨 Reasons:")
            for reason in reasons:
                print(f"     - {reason}")
        else:
            print(f"  ✅ ASSESSMENT: Likely LEGITIMATE")
            print(f"  📊 Confidence: {min(99, int(avg_score * 100))}%")
        
        print(f"\n  Details:")
        print(f"    Average reCAPTCHA Score: {avg_score:.2f}")
        print(f"    User-Agent: {first_attempt['user_agent'][:80]}")
        print(f"    Platform Header: {first_attempt['platform']}")
        print(f"    Blocked: {first_attempt['is_blocked']}")
        print(f"    First Attempt: {first_attempt['timestamp']}")
        print(f"    Last Attempt: {ip_attempts[-1]['timestamp']}")
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total_ips = len(by_ip)
    blocked_count = sum(1 for a in attempts if a['is_blocked'])
    scores = [a['score'] for a in attempts if a['score'] is not None]
    avg_overall_score = sum(scores) / len(scores) if scores else 0
    
    print(f"\n  Total Registration Attempts: {len(attempts)}")
    print(f"  Unique IP Addresses: {total_ips}")
    print(f"  Blocked Attempts: {blocked_count} ({blocked_count/len(attempts)*100:.1f}%)")
    print(f"  Average reCAPTCHA Score: {avg_overall_score:.2f}")
    
    # Score distribution
    if scores:
        low_score = sum(1 for s in scores if s < 0.3)
        med_score = sum(1 for s in scores if 0.3 <= s < 0.7)
        high_score = sum(1 for s in scores if s >= 0.7)
        
        print(f"\n  Score Distribution:")
        print(f"    Bot-like (< 0.3): {low_score} ({low_score/len(scores)*100:.1f}%)")
        print(f"    Suspicious (0.3-0.7): {med_score} ({med_score/len(scores)*100:.1f}%)")
        print(f"    Human-like (>= 0.7): {high_score} ({high_score/len(scores)*100:.1f}%)")
    
    print("\n" + "="*80 + "\n")


def analyze_specific_ip(ip_address, log_path='/opt/wegweiser/wlog/wegweiser.log'):
    """Analyze a specific IP address in detail"""
    
    print(f"\n{'='*80}")
    print(f"DETAILED ANALYSIS: {ip_address}")
    print(f"{'='*80}\n")
    
    attempts = []
    
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if ip_address in line and '/register' in line:
                    print(line.strip()[:200])
    except FileNotFoundError:
        print(f"❌ Log file not found: {log_path}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Analyze specific IP
        analyze_specific_ip(sys.argv[1])
    else:
        # Analyze all attempts
        analyze_log_file()
