#!/usr/bin/env python3
"""
Generate security report from scan artifacts.
"""
import json
import os
import sys
from pathlib import Path


def main():
    """Generate security report from available artifacts."""
    try:
        custom_results_path = 'security-artifacts/custom-security-results/custom-security-results.json'
        
        if os.path.exists(custom_results_path):
            with open(custom_results_path, 'r') as f:
                data = json.load(f)
                
            with open('security-report.md', 'a') as report:
                report.write('## Custom Security Check Findings\n\n')
                
                summary = data.get('summary', {})
                report.write(f'- **Total Issues**: {summary.get("total", 0)}\n')
                report.write(f'- **Critical**: {summary.get("critical", 0)}\n')
                report.write(f'- **High**: {summary.get("high", 0)}\n')
                report.write(f'- **Medium**: {summary.get("medium", 0)}\n')
                report.write(f'- **Low**: {summary.get("low", 0)}\n\n')
                
                # List high and critical issues
                high_issues = [i for i in data.get('issues', []) if i.get('severity') in ['HIGH', 'CRITICAL']]
                if high_issues:
                    report.write('### High/Critical Issues\n\n')
                    for issue in high_issues:
                        report.write(f'- **{issue.get("issue_type")}** ({issue.get("severity")}) in `{issue.get("file_path")}:{issue.get("line_number")}`\n')
                        report.write(f'  - {issue.get("description")}\n')
                        if issue.get('recommendation'):
                            report.write(f'  - Recommendation: {issue.get("recommendation")}\n')
                    report.write('\n')
        else:
            print(f"Custom security results not found at {custom_results_path}")
            
    except Exception as e:
        print(f'Error processing custom security results: {e}')
        return 1
        
    return 0


if __name__ == '__main__':
    sys.exit(main())