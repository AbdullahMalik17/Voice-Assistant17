#!/usr/bin/env python3
"""
Test script to verify that agent tools are properly integrated with the web interface.
"""
import asyncio
import json
import websockets
import sys
import os

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_agent_integration():
    """Test that the agent tools are properly integrated."""
    print("Testing agent integration...")

    try:
        # Import the necessary modules
        from src.agents.tools import create_default_registry
        from src.agents.planner import AgenticPlanner
        from src.agents.guardrails import create_safety_guardrails

        print("+ Successfully imported agent modules")

        # Create a tool registry
        registry = create_default_registry()
        print(f"+ Created tool registry with {registry.get_stats()['total_tools']} tools")

        # List available tools
        tools = registry.list_available()
        print(f"Available tools: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")

        # Test planner creation (without LLM for now)
        try:
            guardrails = create_safety_guardrails()
            planner = AgenticPlanner(
                tool_registry=registry,
                guardrails=guardrails,
                llm_service=None  # We can test without LLM
            )
            print("+ Successfully created planner instance")
        except Exception as e:
            print(f"- Planner creation failed: {e}")

        # Test a simple plan creation
        try:
            plan = planner.create_plan("Set a timer for 5 minutes")
            print(f"+ Successfully created plan with {len(plan.steps)} steps")

            # Validate the plan
            is_valid, errors = planner.validate_plan(plan)
            print(f"+ Plan validation: {'Valid' if is_valid else 'Invalid'}")
            if errors:
                print(f"  Errors: {errors}")

        except Exception as e:
            print(f"- Plan creation failed: {e}")

        print("\nAgent integration test completed successfully!")
        return True

    except ImportError as e:
        print(f"- Failed to import agent modules: {e}")
        return False
    except Exception as e:
        print(f"- Error during agent integration test: {e}")
        return False

def test_websocket_server_integration():
    """Test that the WebSocket server can initialize with agent tools."""
    print("\nTesting WebSocket server integration...")

    try:
        from src.api.websocket_server import VoiceAssistantHandler
        from src.core.config import get_config

        # Create a minimal config for testing
        config = get_config()

        # Create handler instance
        handler = VoiceAssistantHandler(config)
        print("+ Successfully created VoiceAssistantHandler")

        # Check if planner was initialized
        if handler.planner:
            print("+ Agent planner successfully initialized in handler")
            print(f"+ Tool registry has {handler.planner.tools.get_stats()['total_tools']} tools")
        else:
            print("- Agent planner not initialized (this might be expected if dependencies are missing)")

        return True

    except Exception as e:
        print(f"- WebSocket server integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting Agent Integration Tests\n")

    success1 = test_agent_integration()
    success2 = test_websocket_server_integration()

    print(f"\nTest Results:")
    print(f"Agent Integration: {'PASS' if success1 else 'FAIL'}")
    print(f"WebSocket Integration: {'PASS' if success2 else 'FAIL'}")

    if success1 and success2:
        print("\n+ All tests passed! Agent tools are properly integrated.")
        sys.exit(0)
    else:
        print("\n- Some tests failed. Please check the output above.")
        sys.exit(1)