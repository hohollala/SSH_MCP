#!/usr/bin/env python3
"""Simple test runner for integration tests without coverage requirements."""

import sys
import asyncio
import pytest

# Override pytest configuration to remove coverage requirements
pytest_args = [
    "tests/test_end_to_end_integration.py::TestEndToEndIntegration::test_complete_ssh_workflow_with_key_auth",
    "-v",
    "--tb=short"
]

if __name__ == "__main__":
    # Remove coverage options from sys.argv if present
    filtered_args = [arg for arg in sys.argv[1:] if not arg.startswith("--cov")]
    
    # Run pytest with filtered arguments
    exit_code = pytest.main(pytest_args + filtered_args)
    sys.exit(exit_code)