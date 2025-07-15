#!/usr/bin/env python3
"""
MCP Proxy E2E Test Runner

Orchestrates the execution of MCP proxy E2E tests including:
- Starting/stopping test servers
- Running test sequences
- Generating test reports
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E2ETestRunner:
    """Orchestrates E2E test execution."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent.parent
        self.results: Dict = {}
        
    async def run_tests(self, test_pattern: str = "test_mcp_proxy_e2e.py") -> bool:
        """
        Run E2E tests with full orchestration.
        
        Args:
            test_pattern: Pattern to match test files
            
        Returns:
            True if all tests passed, False otherwise
        """
        logger.info("Starting MCP Proxy E2E Test Suite")
        
        start_time = time.time()
        success = False
        
        try:
            # Validate environment
            if not await self._validate_environment():
                logger.error("Environment validation failed")
                return False
            
            # Run the tests using pytest
            success = await self._run_pytest(test_pattern)
            
            # Generate report
            await self._generate_report(success, time.time() - start_time)
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            success = False
        
        logger.info(f"E2E Test Suite completed: {'PASSED' if success else 'FAILED'}")
        return success
    
    async def _validate_environment(self) -> bool:
        """Validate that the environment is ready for testing."""
        logger.info("Validating test environment...")
        
        # Check that test server scripts exist
        test_servers_dir = self.test_dir / "test_servers"
        required_scripts = ["sse_server.py", "http_server.py", "stdio_server.py"]
        
        for script in required_scripts:
            script_path = test_servers_dir / script
            if not script_path.exists():
                logger.error(f"Missing test server script: {script_path}")
                return False
        
        # Check that config file exists
        config_path = self.test_dir / "mcp-proxy.json"
        if not config_path.exists():
            logger.error(f"Missing proxy config: {config_path}")
            return False
        
        # Check that ports are available
        if not await self._check_ports_available([8002, 8003]):
            logger.error("Required ports are not available")
            return False
        
        logger.info("Environment validation passed")
        return True
    
    async def _check_ports_available(self, ports: List[int]) -> bool:
        """Check if required ports are available."""
        import socket
        
        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    if result == 0:
                        logger.warning(f"Port {port} is already in use")
                        return False
            except Exception as e:
                logger.debug(f"Error checking port {port}: {e}")
        
        return True
    
    async def _run_pytest(self, test_pattern: str) -> bool:
        """Run pytest with the specified pattern."""
        logger.info(f"Running pytest with pattern: {test_pattern}")
        
        # Build pytest command
        pytest_cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / test_pattern),
            "-v",
            "-s",
            "--tb=short",
            "--asyncio-mode=auto",
            f"--junitxml={self.test_dir}/test_results.xml"
        ]
        
        try:
            # Run pytest
            process = subprocess.run(
                pytest_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Log output
            if process.stdout:
                logger.info("Test output:")
                for line in process.stdout.split('\n'):
                    if line.strip():
                        logger.info(f"  {line}")
            
            if process.stderr:
                logger.warning("Test errors:")
                for line in process.stderr.split('\n'):
                    if line.strip():
                        logger.warning(f"  {line}")
            
            # Store results
            self.results = {
                "return_code": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "success": process.returncode == 0
            }
            
            return process.returncode == 0
            
        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
            return False
        except Exception as e:
            logger.error(f"Error running pytest: {e}")
            return False
    
    async def _generate_report(self, success: bool, duration: float) -> None:
        """Generate test execution report."""
        logger.info("Generating test report...")
        
        report = {
            "timestamp": time.time(),
            "duration_seconds": duration,
            "success": success,
            "test_results": self.results,
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "working_directory": str(self.project_root)
            }
        }
        
        # Save report to file
        report_path = self.test_dir / "e2e_test_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test report saved to: {report_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("MCP PROXY E2E TEST SUMMARY")
        print("="*60)
        print(f"Status: {'PASSED' if success else 'FAILED'}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Report: {report_path}")
        
        if not success and self.results.get("stderr"):
            print("\nError Details:")
            print(self.results["stderr"])
        
        print("="*60)


async def main():
    """Main entry point for test runner."""
    runner = E2ETestRunner()
    
    # Parse command line arguments
    test_pattern = "test_mcp_proxy_e2e.py"
    if len(sys.argv) > 1:
        test_pattern = sys.argv[1]
    
    # Run tests
    success = await runner.run_tests(test_pattern)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test execution interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)