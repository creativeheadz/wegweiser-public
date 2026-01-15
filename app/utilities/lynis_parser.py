"""
Lynis Security Audit Results Parser

Parses the large JSON output from Lynis security audits and extracts
meaningful, structured data for storage and display.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict


class LynisResultParser:
    """Parse and structure Lynis security audit results."""

    def __init__(self, json_file_path: Optional[str] = None, json_data: Optional[Dict] = None):
        """
        Initialize parser with path to Lynis JSON output or direct JSON data.

        Args:
            json_file_path: Path to JSON file (optional)
            json_data: Direct JSON dict (optional, for Celery tasks)
        """
        if json_data is not None:
            # Direct JSON data provided (from DeviceMetadata.metalogos)
            if isinstance(json_data, str):
                self.raw_data = json.loads(json_data)
            else:
                self.raw_data = json_data
        elif json_file_path is not None:
            # Load from file
            with open(json_file_path, 'r') as f:
                data = json.load(f)
                # Handle double-encoded JSON (if the entire JSON is a string)
                if isinstance(data, str):
                    self.raw_data = json.loads(data)
                else:
                    self.raw_data = data
        else:
            raise ValueError("Either json_file_path or json_data must be provided")

    def get_summary(self) -> Dict[str, Any]:
        """Extract high-level summary metrics."""
        return {
            'status': self.raw_data.get('status'),
            'timestamp': datetime.fromtimestamp(self.raw_data.get('timestamp', 0)),
            'os': self.raw_data.get('os'),
            'os_version': self.raw_data.get('os_version'),
            'hostname': self.raw_data.get('hostname'),
            'lynis_version': self.raw_data.get('lynis_version'),
            'hardening_index': self.raw_data.get('hardening_index'),
            'tests_performed': self.raw_data.get('tests_performed'),
            'warnings_count': len(self.raw_data.get('warnings', [])),
            'suggestions_count': len(self.raw_data.get('suggestions', []))
        }

    def get_warnings(self) -> List[Dict[str, str]]:
        """Extract and parse all warnings."""
        warnings = []
        for warning in self.raw_data.get('warnings', []):
            if isinstance(warning, str):
                # Parse the pipe-delimited format: "TEST_ID|message|details|solution"
                parts = warning.split('|')
                if len(parts) >= 2:
                    warnings.append({
                        'test_id': parts[0],
                        'message': parts[1],
                        'details': parts[2] if len(parts) > 2 else '',
                        'solution': parts[3] if len(parts) > 3 else ''
                    })
        return warnings

    def get_suggestions(self) -> List[Dict[str, str]]:
        """Extract and parse all suggestions."""
        suggestions = []
        for suggestion in self.raw_data.get('suggestions', []):
            if isinstance(suggestion, str):
                # Parse the pipe-delimited format: "TEST_ID|message|details|solution"
                parts = suggestion.split('|')
                if len(parts) >= 2:
                    suggestions.append({
                        'test_id': parts[0],
                        'message': parts[1],
                        'details': parts[2] if len(parts) > 2 else '',
                        'solution': parts[3] if len(parts) > 3 else ''
                    })
        return suggestions

    def get_suggestions_by_category(self) -> Dict[str, List[Dict[str, str]]]:
        """Group suggestions by test category (e.g., AUTH, BOOT, KRNL, etc.)."""
        categorized = defaultdict(list)
        for suggestion in self.get_suggestions():
            test_id = suggestion.get('test_id', 'UNKNOWN')
            category = test_id.split('-')[0] if '-' in test_id else 'OTHER'
            categorized[category].append(suggestion)
        return dict(categorized)

    def get_critical_findings(self, limit: int = 10) -> Dict[str, Any]:
        """
        Extract the most critical findings suitable for AI summarization.

        Returns a compact representation focusing on:
        - Overall hardening score
        - High-priority warnings
        - Top security suggestions by category
        """
        suggestions_by_cat = self.get_suggestions_by_category()

        # Priority categories (security-critical)
        priority_categories = ['AUTH', 'KRNL', 'FIRE', 'ACCT', 'MACF', 'CRYP']

        critical_suggestions = {}
        for cat in priority_categories:
            if cat in suggestions_by_cat:
                critical_suggestions[cat] = suggestions_by_cat[cat][:3]  # Top 3 per category

        return {
            'summary': self.get_summary(),
            'warnings': self.get_warnings(),
            'critical_suggestions': critical_suggestions,
            'all_categories': list(suggestions_by_cat.keys()),
            'total_suggestions_by_category': {
                cat: len(items) for cat, items in suggestions_by_cat.items()
            }
        }

    def get_human_readable_report(self) -> str:
        """Generate a formatted text report for display."""
        summary = self.get_summary()
        warnings = self.get_warnings()
        suggestions_by_cat = self.get_suggestions_by_category()

        report = []
        report.append("=" * 80)
        report.append("LYNIS SECURITY AUDIT REPORT")
        report.append("=" * 80)
        report.append(f"Hostname: {summary['hostname']}")
        report.append(f"OS: {summary['os']} {summary['os_version']}")
        report.append(f"Scan Date: {summary['timestamp']}")
        report.append(f"Lynis Version: {summary['lynis_version']}")
        report.append("")
        report.append(f"HARDENING INDEX: {summary['hardening_index']}/100")
        report.append(f"Tests Performed: {summary['tests_performed']}")
        report.append(f"Warnings: {summary['warnings_count']}")
        report.append(f"Suggestions: {summary['suggestions_count']}")
        report.append("")

        if warnings:
            report.append("=" * 80)
            report.append("WARNINGS")
            report.append("=" * 80)
            for w in warnings:
                report.append(f"\n[{w['test_id']}] {w['message']}")
                if w['details']:
                    report.append(f"  Details: {w['details']}")
                if w['solution']:
                    report.append(f"  Solution: {w['solution']}")

        report.append("")
        report.append("=" * 80)
        report.append("SUGGESTIONS BY CATEGORY")
        report.append("=" * 80)

        # Category name mapping for better readability
        category_names = {
            'AUTH': 'Authentication',
            'BOOT': 'Boot and Services',
            'KRNL': 'Kernel',
            'FILE': 'File Permissions',
            'ACCT': 'Accounting',
            'FIRE': 'Firewall',
            'NETW': 'Networking',
            'PKGS': 'Package Management',
            'LOGG': 'Logging',
            'MACF': 'Mandatory Access Control',
            'CRYP': 'Cryptography',
            'TOOL': 'Security Tools',
            'MALW': 'Malware',
            'HRDN': 'Hardening'
        }

        for category in sorted(suggestions_by_cat.keys()):
            cat_name = category_names.get(category, category)
            items = suggestions_by_cat[category]
            report.append(f"\n{cat_name} ({category}): {len(items)} suggestions")
            report.append("-" * 80)
            for item in items[:5]:  # Show first 5 per category
                report.append(f"  [{item['test_id']}] {item['message']}")
                if item['solution'] and item['solution'] != '-':
                    report.append(f"    → {item['solution']}")
            if len(items) > 5:
                report.append(f"  ... and {len(items) - 5} more")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def get_ai_summary_payload(self) -> Dict[str, Any]:
        """
        Get a compact payload optimized for AI summarization.
        Only includes the most critical information to minimize tokens.
        """
        critical = self.get_critical_findings(limit=5)

        # Simplify for AI consumption
        return {
            'hardening_score': critical['summary']['hardening_index'],
            'os': f"{critical['summary']['os']} {critical['summary']['os_version']}",
            'total_warnings': critical['summary']['warnings_count'],
            'total_suggestions': critical['summary']['suggestions_count'],
            'warnings': [
                f"{w['test_id']}: {w['message']}" for w in critical['warnings']
            ],
            'top_security_concerns': {
                category: [f"{s['test_id']}: {s['message']}" for s in suggestions]
                for category, suggestions in critical['critical_suggestions'].items()
            },
            'categories_with_findings': critical['all_categories']
        }

    def get_html_report(self) -> str:
        """
        Generate HTML-formatted report for webapp display.
        Returns categorized findings with expandable sections.
        """
        summary = self.get_summary()
        warnings = self.get_warnings()
        suggestions_by_cat = self.get_suggestions_by_category()

        # Category name mapping for better readability
        category_names = {
            'AUTH': 'Authentication',
            'BOOT': 'Boot and Services',
            'KRNL': 'Kernel',
            'FILE': 'File Permissions',
            'ACCT': 'Accounting',
            'FIRE': 'Firewall',
            'NETW': 'Networking',
            'PKGS': 'Package Management',
            'LOGG': 'Logging',
            'MACF': 'Mandatory Access Control',
            'CRYP': 'Cryptography',
            'TOOL': 'Security Tools',
            'MALW': 'Malware',
            'HRDN': 'Hardening',
            'BANN': 'Banners',
            'NAME': 'Name Services',
            'USB': 'USB Devices',
            'FINT': 'File Integrity',
            'HOME': 'Home Directories'
        }

        html = ['<div class="lynis-report">']

        # Summary section
        html.append('<div class="lynis-summary">')
        html.append(f'<p><strong>OS:</strong> {summary["os"]} {summary["os_version"]}</p>')
        html.append(f'<p><strong>Hostname:</strong> {summary["hostname"]}</p>')
        html.append(f'<p><strong>Lynis Version:</strong> {summary["lynis_version"]}</p>')
        html.append(f'<p><strong>Tests Performed:</strong> {summary["tests_performed"]}</p>')
        html.append(f'<p><strong>Warnings:</strong> {summary["warnings_count"]}</p>')
        html.append(f'<p><strong>Suggestions:</strong> {summary["suggestions_count"]}</p>')
        html.append('</div>')

        # Warnings section (if any)
        if warnings:
            html.append('<div class="lynis-warnings">')
            html.append('<h4>Warnings</h4>')
            html.append('<ul class="warning-list">')
            for w in warnings:
                html.append(f'<li class="warning-item">')
                html.append(f'<strong>[{w["test_id"]}]</strong> {w["message"]}')
                if w['details'] and w['details'] != '-':
                    html.append(f'<p class="warning-details">Details: {w["details"]}</p>')
                if w['solution'] and w['solution'] != '-':
                    html.append(f'<p class="warning-solution">Solution: {w["solution"]}</p>')
                html.append('</li>')
            html.append('</ul>')
            html.append('</div>')

        # Suggestions by category
        html.append('<div class="lynis-suggestions">')
        html.append('<h4>Security Recommendations by Category</h4>')

        for category in sorted(suggestions_by_cat.keys()):
            cat_name = category_names.get(category, category)
            items = suggestions_by_cat[category]

            html.append(f'<div class="category-card" data-category="{category}">')
            html.append(f'<div class="category-header">')
            html.append(f'<h5>{cat_name}</h5>')
            html.append(f'<span class="badge">{len(items)} suggestion{"s" if len(items) != 1 else ""}</span>')
            html.append('</div>')

            html.append('<div class="category-content">')
            html.append('<ul class="suggestion-list">')
            for item in items:
                html.append('<li class="suggestion-item">')
                html.append(f'<strong>[{item["test_id"]}]</strong> {item["message"]}')
                if item['solution'] and item['solution'] != '-':
                    html.append(f'<p class="suggestion-solution">→ {item["solution"]}</p>')
                html.append('</li>')
            html.append('</ul>')
            html.append('</div>')
            html.append('</div>')

        html.append('</div>')
        html.append('</div>')

        return '\n'.join(html)


def test_parser():
    """Test the parser with the existing results file."""
    parser = LynisResultParser('/opt/wegweiser/tmp/lynis_results.json')

    print("=== SUMMARY ===")
    summary = parser.get_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n=== AI PAYLOAD (compact for token efficiency) ===")
    ai_payload = parser.get_ai_summary_payload()
    print(json.dumps(ai_payload, indent=2))

    print("\n=== HUMAN READABLE REPORT ===")
    print(parser.get_human_readable_report())


if __name__ == '__main__':
    test_parser()
