#!/usr/bin/env python3
"""
Test Report Generator for Live Monitoring
Generates HTML and JSON reports from test results
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import asdict
from live_tests import TestResult, TestStatus


class ReportGenerator:
    """Generates monitoring reports"""
    
    def __init__(self, output_dir: str = "/opt/wegweiser/wlog/monitoring_reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_json_report(self, results: List[TestResult], filename: str = None) -> str:
        """Generate JSON report"""
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_tests": len(results),
            "passed": len([r for r in results if r.status == TestStatus.PASS]),
            "failed": len([r for r in results if r.status == TestStatus.FAIL]),
            "warnings": len([r for r in results if r.status == TestStatus.WARN]),
            "tests": [asdict(r) for r in results]
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filepath
    
    def generate_html_report(self, results: List[TestResult], filename: str = None) -> str:
        """Generate HTML report"""
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        passed = len([r for r in results if r.status == TestStatus.PASS])
        failed = len([r for r in results if r.status == TestStatus.FAIL])
        warnings = len([r for r in results if r.status == TestStatus.WARN])
        total = len(results)
        
        # Calculate pass rate
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # Generate test rows
        test_rows = ""
        for result in results:
            status_class = f"status-{result.status.value}"
            status_icon = {
                TestStatus.PASS: "✓",
                TestStatus.FAIL: "✗",
                TestStatus.WARN: "⚠"
            }.get(result.status, "?")
            
            test_rows += f"""
            <tr class="{status_class}">
                <td>{status_icon}</td>
                <td>{result.test_name}</td>
                <td>{result.status.value.upper()}</td>
                <td>{result.duration_ms:.0f}ms</td>
                <td>{result.message}</td>
                <td>{result.timestamp}</td>
            </tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Wegweiser Monitoring Report</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    margin: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 10px;
                }}
                .timestamp {{
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 20px;
                }}
                .summary {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin-bottom: 30px;
                }}
                .summary-card {{
                    padding: 15px;
                    border-radius: 6px;
                    text-align: center;
                }}
                .summary-card h3 {{
                    margin: 0 0 10px 0;
                    font-size: 14px;
                    color: #666;
                }}
                .summary-card .value {{
                    font-size: 32px;
                    font-weight: bold;
                }}
                .card-passed {{
                    background: #e8f5e9;
                    border-left: 4px solid #4caf50;
                }}
                .card-failed {{
                    background: #ffebee;
                    border-left: 4px solid #f44336;
                }}
                .card-warning {{
                    background: #fff3e0;
                    border-left: 4px solid #ff9800;
                }}
                .card-total {{
                    background: #e3f2fd;
                    border-left: 4px solid #2196f3;
                }}
                .pass-rate {{
                    font-size: 18px;
                    margin-top: 10px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th {{
                    background: #f5f5f5;
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                    border-bottom: 2px solid #ddd;
                }}
                td {{
                    padding: 12px;
                    border-bottom: 1px solid #eee;
                }}
                tr.status-pass {{
                    background: #f1f8f6;
                }}
                tr.status-fail {{
                    background: #fef5f5;
                }}
                tr.status-warn {{
                    background: #fffbf0;
                }}
                .status-pass {{
                    color: #4caf50;
                    font-weight: 600;
                }}
                .status-fail {{
                    color: #f44336;
                    font-weight: 600;
                }}
                .status-warn {{
                    color: #ff9800;
                    font-weight: 600;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 Wegweiser Monitoring Report</h1>
                <div class="timestamp">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
                
                <div class="summary">
                    <div class="summary-card card-passed">
                        <h3>Passed</h3>
                        <div class="value">{passed}</div>
                    </div>
                    <div class="summary-card card-failed">
                        <h3>Failed</h3>
                        <div class="value">{failed}</div>
                    </div>
                    <div class="summary-card card-warning">
                        <h3>Warnings</h3>
                        <div class="value">{warnings}</div>
                    </div>
                    <div class="summary-card card-total">
                        <h3>Total</h3>
                        <div class="value">{total}</div>
                        <div class="pass-rate">{pass_rate:.1f}% pass rate</div>
                    </div>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th style="width: 30px;"></th>
                            <th>Test Name</th>
                            <th style="width: 100px;">Status</th>
                            <th style="width: 100px;">Duration</th>
                            <th>Message</th>
                            <th style="width: 180px;">Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
                        {test_rows}
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>Wegweiser Live Monitoring System</p>
                    <p>Report generated automatically by monitoring suite</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(filepath, 'w') as f:
            f.write(html)
        
        return filepath
    
    def generate_csv_report(self, results: List[TestResult], filename: str = None) -> str:
        """Generate CSV report"""
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            # Header
            f.write("Test Name,Status,Duration (ms),Message,Timestamp\n")
            
            # Rows
            for result in results:
                f.write(f'"{result.test_name}","{result.status.value}",{result.duration_ms:.0f},"{result.message}","{result.timestamp}"\n')
        
        return filepath
    
    def generate_all_reports(self, results: List[TestResult]) -> Dict[str, str]:
        """Generate all report formats"""
        return {
            "json": self.generate_json_report(results),
            "html": self.generate_html_report(results),
            "csv": self.generate_csv_report(results)
        }


if __name__ == "__main__":
    # Example usage
    from live_tests import TestResult, TestStatus
    
    # Create sample results
    sample_results = [
        TestResult(
            test_name="Health Check",
            status=TestStatus.PASS,
            duration_ms=45.2,
            message="Health endpoint responding"
        ),
        TestResult(
            test_name="Login Flow",
            status=TestStatus.PASS,
            duration_ms=123.5,
            message="Login page accessible"
        ),
        TestResult(
            test_name="Database Connection",
            status=TestStatus.FAIL,
            duration_ms=5000.0,
            message="Connection timeout"
        ),
    ]
    
    # Generate reports
    generator = ReportGenerator()
    reports = generator.generate_all_reports(sample_results)
    
    print("Reports generated:")
    for format_type, filepath in reports.items():
        print(f"  {format_type}: {filepath}")

