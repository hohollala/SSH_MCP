#!/usr/bin/env python3
"""
Simple test runner for MCP client compatibility tests.
"""

import asyncio
import sys
import traceback
from unittest.mock import patch

# Import test classes
from tests.test_mcp_client_compatibility import (
    TestClaudeCodeCompatibility,
    TestGeminiCLICompatibility,
    TestClaudeDesktopCompatibility,
    TestMCPProtocolCompliance
)


async def run_test_method(test_class, method_name):
    """Run a single test method."""
    try:
        # Create test instance
        test_instance = test_class()
        
        # Set up server fixture
        test_instance.server = test_instance.server()
        
        # Set up mock SSH manager fixture
        test_instance.mock_ssh_manager = test_instance.mock_ssh_manager(test_instance.server)
        
        # Mock SSH config validation
        with patch('ssh_mcp_server.models.SSHConfig._validate_auth_requirements'):
            # Run the test method
            test_method = getattr(test_instance, method_name)
            await test_method()
            
        print(f"✓ {test_class.__name__}::{method_name}")
        return True
        
    except Exception as e:
        print(f"✗ {test_class.__name__}::{method_name}: {str(e)}")
        traceback.print_exc()
        return False


async def main():
    """Run all compatibility tests."""
    print("🚀 Running MCP Client Compatibility Tests")
    print("=" * 50)
    
    # Define test methods to run
    test_cases = [
        (TestClaudeCodeCompatibility, "test_claude_code_initialization_sequence"),
        (TestClaudeCodeCompatibility, "test_claude_code_interactive_development_workflow"),
        (TestClaudeCodeCompatibility, "test_claude_code_error_handling_patterns"),
        (TestGeminiCLICompatibility, "test_gemini_cli_batch_analysis_workflow"),
        (TestGeminiCLICompatibility, "test_gemini_cli_structured_data_collection"),
        (TestClaudeDesktopCompatibility, "test_claude_desktop_user_friendly_workflow"),
        (TestClaudeDesktopCompatibility, "test_claude_desktop_file_management"),
        (TestMCPProtocolCompliance, "test_json_rpc_2_0_compliance"),
        (TestMCPProtocolCompliance, "test_mcp_initialize_compliance"),
        (TestMCPProtocolCompliance, "test_mcp_tools_list_compliance"),
        (TestMCPProtocolCompliance, "test_error_response_compliance"),
        (TestMCPProtocolCompliance, "test_tool_schema_validation_compliance"),
        (TestMCPProtocolCompliance, "test_content_type_compliance"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_class, method_name in test_cases:
        success = await run_test_method(test_class, method_name)
        if success:
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All MCP client compatibility tests passed!")
        return True
    else:
        print(f"❌ {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)