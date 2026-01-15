#!/usr/bin/env python3
"""
Test script for the text formatter
"""
from app.utilities.text_formatter import text_formatter

# Sample analysis text
sample_text = """
# System Analysis

## Hardware Overview

The system has 16GB of RAM and an Intel i7 processor. Storage consists of a 512GB SSD that is currently at 65% capacity.

## Software Status

The operating system is Windows 10 Pro, version 21H2. All critical updates have been installed.

### Issues Detected

- WARNING: 3 applications have not been updated in over 90 days
- ERROR: Antivirus definitions are out of date
- CRITICAL: Backup service has failed to run for the past 7 days

## Recommendations

1. Update antivirus definitions immediately
2. Check backup service configuration
3. Update outdated applications

## Health Assessment

Overall system health is CAUTION due to the identified issues.
"""

# Format the text
formatted_text = text_formatter.format_analysis(sample_text)

# Print the result
print("Original Text:")
print("-" * 50)
print(sample_text)
print("\nFormatted Text:")
print("-" * 50)
print(formatted_text)
