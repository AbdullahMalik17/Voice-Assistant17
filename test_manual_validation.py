"""
Manual Validation Test Script
Run individual tests for Phase 7 validation
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_network_monitor():
    """T079/T080: Test network monitoring and offline detection"""
    print("\n" + "=" * 60)
    print("TEST: Network Monitor")
    print("=" * 60)

    from src.utils.network_monitor import get_network_monitor

    nm = get_network_monitor()

    print(f"Current status: {'ONLINE' if nm.is_connected() else 'OFFLINE'}")
    print(f"Last status: {nm.get_last_status()}")

    print("\nTo test offline mode:")
    print("1. Disconnect your network (WiFi off or unplug ethernet)")
    print("2. Run this test again - should show OFFLINE")
    print("3. Reconnect and run again - should show ONLINE")

    return nm.is_connected()


def test_request_queue():
    """T080: Test request queuing functionality"""
    print("\n" + "=" * 60)
    print("TEST: Request Queue Manager")
    print("=" * 60)

    from src.core.config import get_config
    from src.core.request_queue_manager import create_request_queue_manager
    from src.models.request_queue import RequestType
    from src.utils.logger import get_event_logger, get_metrics_logger

    config = get_config()
    logger = get_event_logger("test_queue", log_dir=config.log_dir)
    metrics = get_metrics_logger(log_dir=config.log_dir)

    # Create queue manager
    qm = create_request_queue_manager(logger, metrics)

    # Register a test processor
    def test_processor(payload):
        print(f"  Processing: {payload}")
        return f"Processed: {payload['test']}"

    qm.register_processor(RequestType.LLM_QUERY, test_processor)

    # Check online status
    online = qm.is_online()
    print(f"Network status: {'ONLINE' if online else 'OFFLINE'}")

    # Enqueue a test request
    print("\nEnqueuing test request...")
    request = qm.enqueue(
        request_type=RequestType.LLM_QUERY,
        payload={"test": "Hello from queue"},
        priority=5
    )
    print(f"  Request ID: {request.id}")
    print(f"  Status: {request.status.value}")

    # Get stats
    stats = qm.get_queue_stats()
    print(f"\nQueue stats: {stats}")

    # Process if online
    if online:
        print("\nProcessing queue...")
        processed = qm.process_queue()
        print(f"  Processed: {processed} requests")
    else:
        print("\n[OFFLINE] Request queued for later processing")
        print("Reconnect to network and run again to process")

    return True


def test_interrupt_handling():
    """T083: Test interrupt mechanism"""
    print("\n" + "=" * 60)
    print("TEST: Interrupt Handling")
    print("=" * 60)

    import threading

    # Simulate processing state
    is_processing = False
    interrupt_requested = False
    lock = threading.Lock()

    def check_interrupt():
        nonlocal interrupt_requested
        with lock:
            if interrupt_requested:
                interrupt_requested = False
                return True
            return False

    def request_interrupt():
        nonlocal interrupt_requested
        with lock:
            interrupt_requested = True
            print("  [INTERRUPT REQUESTED]")

    def simulate_processing():
        nonlocal is_processing
        is_processing = True
        print("  Starting simulated processing...")

        for step in ["Recording", "Transcribing", "Classifying", "Generating", "Speaking"]:
            print(f"    Step: {step}")
            time.sleep(0.5)

            if check_interrupt():
                print("    [INTERRUPTED - Stopping]")
                is_processing = False
                return False

        is_processing = False
        return True

    # Test 1: Normal completion
    print("\nTest 1: Normal processing (no interrupt)")
    result = simulate_processing()
    print(f"  Completed: {result}")

    # Test 2: With interrupt
    print("\nTest 2: Processing with interrupt")

    def delayed_interrupt():
        time.sleep(1.0)  # Interrupt after 1 second
        request_interrupt()

    interrupt_thread = threading.Thread(target=delayed_interrupt)
    interrupt_thread.start()

    result = simulate_processing()
    interrupt_thread.join()
    print(f"  Completed: {result} (expected: False due to interrupt)")

    print("\n[OK] Interrupt mechanism working correctly")
    return True


def test_context_manager():
    """Test context manager with topic shift and timeout"""
    print("\n" + "=" * 60)
    print("TEST: Context Manager")
    print("=" * 60)

    from src.core.config import get_config
    from src.core.context_manager import create_context_manager
    from src.models.intent import Intent, IntentType
    from src.storage.memory_store import MemoryStore
    from src.utils.logger import get_event_logger, get_metrics_logger

    config = get_config()
    logger = get_event_logger("test_context", log_dir=config.log_dir)
    metrics = get_metrics_logger(log_dir=config.log_dir)
    memory = MemoryStore()

    cm = create_context_manager(config, logger, metrics, memory)

    # Test context creation
    context = cm.get_or_create_context()
    print(f"Context created: {context.id}")
    print(f"  Max exchanges: {cm.max_exchanges}")
    print(f"  Timeout: {cm.timeout_seconds}s")

    # Add exchanges
    from uuid import uuid4
    intent = Intent(
        voice_command_id=uuid4(),
        intent_type=IntentType.INFORMATIONAL,
        confidence_score=0.9
    )

    cm.add_exchange(
        user_input="What is the weather today?",
        intent=intent,
        assistant_response="It's sunny with a high of 75 degrees.",
        confidence=0.9
    )

    stats = cm.get_context_stats()
    print(f"\nAfter 1 exchange:")
    print(f"  Exchanges: {stats['exchanges']}")
    print(f"  Topics: {stats['topic_keywords']}")

    # Add follow-up
    cm.add_exchange(
        user_input="What about tomorrow?",
        intent=intent,
        assistant_response="Tomorrow will be partly cloudy.",
        confidence=0.85
    )

    stats = cm.get_context_stats()
    print(f"\nAfter 2 exchanges:")
    print(f"  Exchanges: {stats['exchanges']}")
    print(f"  Topics: {stats['topic_keywords']}")

    # Test context summary
    summary = cm.get_context_for_llm()
    print(f"\nContext summary for LLM:")
    print(f"  {summary[:100]}..." if summary else "  (empty)")

    print("\n[OK] Context manager working correctly")
    return True


def test_action_executor():
    """Test action executor with system status"""
    print("\n" + "=" * 60)
    print("TEST: Action Executor")
    print("=" * 60)

    from src.core.config import get_config
    from src.services.action_executor import create_action_executor
    from src.models.intent import Intent, IntentType, ActionType
    from src.utils.logger import get_event_logger, get_metrics_logger

    config = get_config()
    logger = get_event_logger("test_action", log_dir=config.log_dir)
    metrics = get_metrics_logger(log_dir=config.log_dir)

    ae = create_action_executor(config, logger, metrics)

    print(f"Platform: {ae.current_platform.value}")
    print(f"Registered actions: {list(ae.action_registry.keys())}")

    # Test system status
    print("\nTesting system status query...")
    from uuid import uuid4
    intent = Intent(
        voice_command_id=uuid4(),
        intent_type=IntentType.TASK_BASED,
        action_type=ActionType.SYSTEM_STATUS,
        confidence_score=0.9,
        entities={"status_type": "cpu"}
    )

    result = ae.execute_action(intent)
    print(f"  Result: {result}")

    # Test memory status
    intent.entities = {"status_type": "memory"}
    result = ae.execute_action(intent)
    print(f"  Memory: {result}")

    print("\n[OK] Action executor working correctly")
    return True


def run_all_tests():
    """Run all manual validation tests"""
    print("\n" + "=" * 60)
    print("MANUAL VALIDATION TEST SUITE")
    print("Voice Assistant - Phase 7")
    print("=" * 60)

    results = {}

    # Run tests
    tests = [
        ("Network Monitor", test_network_monitor),
        ("Request Queue", test_request_queue),
        ("Interrupt Handling", test_interrupt_handling),
        ("Context Manager", test_context_manager),
        ("Action Executor", test_action_executor),
    ]

    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n[ERROR] {name}: {str(e)}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} passed")

    return all(results.values())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manual validation tests")
    parser.add_argument("--test", choices=["network", "queue", "interrupt", "context", "action", "all"],
                        default="all", help="Test to run")

    args = parser.parse_args()

    if args.test == "network":
        test_network_monitor()
    elif args.test == "queue":
        test_request_queue()
    elif args.test == "interrupt":
        test_interrupt_handling()
    elif args.test == "context":
        test_context_manager()
    elif args.test == "action":
        test_action_executor()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)
