#!/usr/bin/env python3
"""
Custom security checks for IntentVerse codebase.

This script performs targeted security checks specific to the IntentVerse architecture:
1. Checks for hardcoded API keys and credentials
2. Validates CORS configuration
3. Checks for proper JWT token validation
4. Validates input sanitization in API endpoints
5. Checks for proper database query parameterization
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple


class SecurityIssue:
    """Represents a security issue found in the codebase."""
    
    SEVERITY_LOW = "LOW"
    SEVERITY_MEDIUM = "MEDIUM"
    SEVERITY_HIGH = "HIGH"
    SEVERITY_CRITICAL = "CRITICAL"
    
    def __init__(
        self,
        file_path: str,
        line_number: int,
        issue_type: str,
        description: str,
        severity: str,
        code_snippet: str = None,
        recommendation: str = None
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.issue_type = issue_type
        self.description = description
        self.severity = severity
        self.code_snippet = code_snippet
        self.recommendation = recommendation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the issue to a dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "issue_type": self.issue_type,
            "description": self.description,
            "severity": self.severity,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation
        }
    
    def __str__(self) -> str:
        """String representation of the issue."""
        return (
            f"[{self.severity}] {self.issue_type} in {self.file_path}:{self.line_number}\n"
            f"Description: {self.description}\n"
            f"Recommendation: {self.recommendation or 'N/A'}"
        )


class SecurityChecker:
    """Performs security checks on the codebase."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.issues: List[SecurityIssue] = []
    
    def check_all(self) -> List[SecurityIssue]:
        """Run all security checks."""
        self.check_hardcoded_credentials()
        self.check_cors_configuration()
        self.check_jwt_validation()
        self.check_input_sanitization()
        self.check_sql_injection()
        self.check_content_security_policy()
        self.check_rate_limiting()
        self.check_session_management()
        return self.issues
    
    def _read_file(self, file_path: Path) -> Tuple[List[str], bool]:
        """Read a file and return its lines."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.readlines(), True
        except Exception:
            return [], False
    
    def check_hardcoded_credentials(self) -> None:
        """Check for hardcoded credentials in the codebase."""
        patterns = [
            (r'(api_key|apikey|secret|password|token)\s*=\s*["\']([^"\']+)["\']', 
             "Hardcoded credential", 
             SecurityIssue.SEVERITY_HIGH,
             "Store sensitive values in environment variables or a secure vault"),
            
            (r'(dev|test|dummy)[-_]?(key|secret|password|token)\s*=\s*["\']([^"\']+)["\']',
             "Development credential in code",
             SecurityIssue.SEVERITY_MEDIUM,
             "Remove development credentials from code"),
        ]
        
        # Skip checking in test files
        excluded_dirs = ["tests", "__pycache__", "node_modules"]
        
        for py_file in self.base_path.glob("**/*.py"):
            if any(excluded_dir in py_file.parts for excluded_dir in excluded_dirs):
                continue
                
            lines, success = self._read_file(py_file)
            if not success:
                continue
                
            for i, line in enumerate(lines, 1):
                for pattern, issue_type, severity, recommendation in patterns:
                    matches = re.search(pattern, line)
                    if matches:
                        # Skip if this is in a comment
                        if line.strip().startswith("#"):
                            continue
                            
                        self.issues.append(SecurityIssue(
                            file_path=str(py_file.relative_to(self.base_path)),
                            line_number=i,
                            issue_type=issue_type,
                            description=f"Found potential {matches.group(1)} in code",
                            severity=severity,
                            code_snippet=line.strip(),
                            recommendation=recommendation
                        ))
    
    def check_cors_configuration(self) -> None:
        """Check CORS configuration for security issues."""
        # Look for CORS configuration in main.py or similar files
        main_files = list(self.base_path.glob("**/main.py")) + list(self.base_path.glob("**/app.py"))
        
        for main_file in main_files:
            lines, success = self._read_file(main_file)
            if not success:
                continue
                
            found_cors = False
            wildcard_origins = False
            
            for i, line in enumerate(lines, 1):
                if "CORSMiddleware" in line:
                    found_cors = True
                
                if found_cors and "allow_origins" in line and "*" in line:
                    # This is expected in IntentVerse's architecture
                    # Just add an informational note
                    self.issues.append(SecurityIssue(
                        file_path=str(main_file.relative_to(self.base_path)),
                        line_number=i,
                        issue_type="CORS Configuration Note",
                        description="Wildcard CORS origin (*) detected - this is expected for browser-direct API access",
                        severity=SecurityIssue.SEVERITY_LOW,
                        code_snippet=line.strip(),
                        recommendation="Ensure this is intentional for your architecture. Consider adding CSRF protection."
                    ))
                    wildcard_origins = True
            
            # If CORS is configured but no wildcard origins found, that's unusual for this architecture
            if found_cors and not wildcard_origins:
                self.issues.append(SecurityIssue(
                    file_path=str(main_file.relative_to(self.base_path)),
                    line_number=0,
                    issue_type="CORS Configuration",
                    description="CORS is configured but without wildcard origins - this may break browser-direct API access",
                    severity=SecurityIssue.SEVERITY_LOW,
                    recommendation="Verify CORS configuration matches your architecture requirements"
                ))
    
    def check_jwt_validation(self) -> None:
        """Check for proper JWT token validation."""
        security_files = list(self.base_path.glob("**/security.py")) + list(self.base_path.glob("**/auth.py"))
        
        for security_file in security_files:
            lines, success = self._read_file(security_file)
            if not success:
                continue
            
            content = "".join(lines)
            
            # Check if JWT validation includes proper checks
            has_decode = "decode" in content and "jwt" in content
            has_expiration = "exp" in content or "expires" in content or "expiration" in content
            has_verification = "verify" in content or "validate" in content
            
            if has_decode and not (has_expiration and has_verification):
                self.issues.append(SecurityIssue(
                    file_path=str(security_file.relative_to(self.base_path)),
                    line_number=0,
                    issue_type="JWT Validation",
                    description="JWT decoding may be missing expiration or signature verification",
                    severity=SecurityIssue.SEVERITY_HIGH,
                    recommendation="Ensure JWT tokens are validated with expiration checks and signature verification"
                ))
    
    def check_input_sanitization(self) -> None:
        """Check for proper input sanitization in API endpoints."""
        api_files = list(self.base_path.glob("**/api.py")) + list(self.base_path.glob("**/api_v*.py"))
        
        for api_file in api_files:
            lines, success = self._read_file(api_file)
            if not success:
                continue
            
            content = "".join(lines)
            
            # Check if Pydantic models are used for validation
            has_pydantic = "pydantic" in content or "BaseModel" in content
            
            if not has_pydantic:
                self.issues.append(SecurityIssue(
                    file_path=str(api_file.relative_to(self.base_path)),
                    line_number=0,
                    issue_type="Input Validation",
                    description="API endpoints may be missing Pydantic model validation",
                    severity=SecurityIssue.SEVERITY_MEDIUM,
                    recommendation="Use Pydantic models to validate all API inputs"
                ))
    
    def check_sql_injection(self) -> None:
        """Check for potential SQL injection vulnerabilities."""
        patterns = [
            (r'execute\([\'"].*\%.*[\'"]\s*%\s*', 
             "Potential SQL Injection", 
             SecurityIssue.SEVERITY_HIGH,
             "Use parameterized queries with SQLAlchemy"),
            
            (r'execute\([\'"].*\{\}.*[\'"]\.format', 
             "Potential SQL Injection", 
             SecurityIssue.SEVERITY_HIGH,
             "Use parameterized queries with SQLAlchemy"),
            
            (r'raw_connection|raw_sql|raw query|text\([\'"]', 
             "Raw SQL Usage", 
             SecurityIssue.SEVERITY_MEDIUM,
             "Prefer ORM methods over raw SQL when possible"),
        ]
        
        for py_file in self.base_path.glob("**/*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue
                
            lines, success = self._read_file(py_file)
            if not success:
                continue
                
            for i, line in enumerate(lines, 1):
                for pattern, issue_type, severity, recommendation in patterns:
                    if re.search(pattern, line):
                        # Skip if this is in a comment
                        if line.strip().startswith("#"):
                            continue
                            
                        self.issues.append(SecurityIssue(
                            file_path=str(py_file.relative_to(self.base_path)),
                            line_number=i,
                            issue_type=issue_type,
                            description="Potential SQL injection risk detected",
                            severity=severity,
                            code_snippet=line.strip(),
                            recommendation=recommendation
                        ))
    
    def check_content_security_policy(self) -> None:
        """Check for Content-Security-Policy headers."""
        main_files = list(self.base_path.glob("**/main.py")) + list(self.base_path.glob("**/app.py"))
        
        for main_file in main_files:
            lines, success = self._read_file(main_file)
            if not success:
                continue
            
            content = "".join(lines)
            
            # Check if CSP headers are set
            has_csp = "Content-Security-Policy" in content
            
            if not has_csp:
                self.issues.append(SecurityIssue(
                    file_path=str(main_file.relative_to(self.base_path)),
                    line_number=0,
                    issue_type="Missing Security Headers",
                    description="Content-Security-Policy header not detected",
                    severity=SecurityIssue.SEVERITY_LOW,
                    recommendation="Consider adding Content-Security-Policy headers to prevent XSS attacks"
                ))
    
    def check_rate_limiting(self) -> None:
        """Check for rate limiting implementation."""
        has_rate_limiting = False
        
        # Check if rate_limiter.py exists
        rate_limiter_files = list(self.base_path.glob("**/rate_limiter.py"))
        if rate_limiter_files:
            has_rate_limiting = True
        
        # Also check for rate limiting in main app files
        if not has_rate_limiting:
            main_files = list(self.base_path.glob("**/main.py")) + list(self.base_path.glob("**/app.py"))
            
            for main_file in main_files:
                lines, success = self._read_file(main_file)
                if not success:
                    continue
                
                content = "".join(lines)
                
                if "rate" in content.lower() and "limit" in content.lower():
                    has_rate_limiting = True
                    break
        
        if not has_rate_limiting:
            self.issues.append(SecurityIssue(
                file_path="",
                line_number=0,
                issue_type="Rate Limiting",
                description="Rate limiting implementation not detected",
                severity=SecurityIssue.SEVERITY_MEDIUM,
                recommendation="Implement rate limiting to prevent abuse and DoS attacks"
            ))
    
    def check_session_management(self) -> None:
        """Check for secure session management."""
        security_files = list(self.base_path.glob("**/security.py")) + list(self.base_path.glob("**/auth.py"))
        
        for security_file in security_files:
            lines, success = self._read_file(security_file)
            if not success:
                continue
            
            content = "".join(lines)
            
            # Check for refresh token rotation
            has_refresh_rotation = "refresh" in content and ("rotate" in content or "new" in content)
            
            if not has_refresh_rotation:
                self.issues.append(SecurityIssue(
                    file_path=str(security_file.relative_to(self.base_path)),
                    line_number=0,
                    issue_type="Session Management",
                    description="Refresh token rotation may not be implemented",
                    severity=SecurityIssue.SEVERITY_LOW,
                    recommendation="Consider implementing refresh token rotation for better security"
                ))


def main():
    parser = argparse.ArgumentParser(description="Run custom security checks on IntentVerse codebase")
    parser.add_argument("--path", type=str, default=".", help="Path to the IntentVerse codebase")
    parser.add_argument("--output", type=str, help="Output file for JSON results")
    parser.add_argument("--fail-on-issues", action="store_true", help="Exit with non-zero code if issues found")
    args = parser.parse_args()
    
    checker = SecurityChecker(args.path)
    issues = checker.check_all()
    
    # Count issues by severity
    severity_counts = {
        SecurityIssue.SEVERITY_CRITICAL: 0,
        SecurityIssue.SEVERITY_HIGH: 0,
        SecurityIssue.SEVERITY_MEDIUM: 0,
        SecurityIssue.SEVERITY_LOW: 0
    }
    
    for issue in issues:
        severity_counts[issue.severity] += 1
    
    # Print summary
    print(f"\n=== IntentVerse Security Check Results ===")
    print(f"Total issues found: {len(issues)}")
    print(f"  Critical: {severity_counts[SecurityIssue.SEVERITY_CRITICAL]}")
    print(f"  High:     {severity_counts[SecurityIssue.SEVERITY_HIGH]}")
    print(f"  Medium:   {severity_counts[SecurityIssue.SEVERITY_MEDIUM]}")
    print(f"  Low:      {severity_counts[SecurityIssue.SEVERITY_LOW]}")
    print("")
    
    # Print issues
    for issue in issues:
        print(f"{issue}\n")
    
    # Write JSON output if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total": len(issues),
                    "critical": severity_counts[SecurityIssue.SEVERITY_CRITICAL],
                    "high": severity_counts[SecurityIssue.SEVERITY_HIGH],
                    "medium": severity_counts[SecurityIssue.SEVERITY_MEDIUM],
                    "low": severity_counts[SecurityIssue.SEVERITY_LOW]
                },
                "issues": [issue.to_dict() for issue in issues]
            }, f, indent=2)
        print(f"Results written to {args.output}")
    
    # Exit with non-zero code if issues found and --fail-on-issues is set
    if args.fail_on_issues and (
        severity_counts[SecurityIssue.SEVERITY_CRITICAL] > 0 or 
        severity_counts[SecurityIssue.SEVERITY_HIGH] > 0
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()