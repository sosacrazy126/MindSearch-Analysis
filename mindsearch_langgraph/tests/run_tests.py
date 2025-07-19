#!/usr/bin/env python3
"""Simple test runner to demonstrate the MindSearch LangGraph test suite."""

import subprocess
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_command(cmd, description):
    """Run a command and display results."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0


def main():
    """Run various test scenarios to demonstrate capabilities."""
    print("🚀 MindSearch LangGraph Test Suite Demo")
    print("=" * 60)
    
    # Set environment for testing
    os.environ["OPENAI_API_KEY"] = "mock-key-for-testing"
    os.environ["USE_REAL_APIS"] = "false"
    
    # Change to project directory
    os.chdir(Path(__file__).parent.parent)
    
    # Test scenarios to run
    scenarios = [
        # Quick validation
        ("pytest tests/test_state.py::TestStateManagement::test_state_initialization -v",
         "Basic State Management Test"),
        
        # Loop prevention validation
        ("pytest tests/test_benefits.py::TestClaimedBenefits::test_no_infinite_loops -v -s",
         "Infinite Loop Prevention Test"),
        
        # Performance validation
        ("pytest tests/test_search_engines.py::TestSearchPerformance::test_parallel_search_speedup -v -s",
         "Parallel Search Performance Test"),
        
        # Code reduction validation
        ("pytest tests/test_benefits.py::TestClaimedBenefits::test_80_percent_code_reduction -v -s",
         "Code Reduction Validation"),
        
        # End-to-end test
        ("pytest tests/test_graph.py::TestMindSearchAgent::test_basic_search -v",
         "End-to-End Search Test"),
        
        # Benefits summary
        ("pytest tests/test_benefits.py -v --tb=short -k 'test_streaming_visibility or test_checkpointing'",
         "Advanced Features Test"),
    ]
    
    passed = 0
    failed = 0
    
    for cmd, description in scenarios:
        if run_command(cmd, description):
            passed += 1
            print("✅ PASSED")
        else:
            failed += 1
            print("❌ FAILED")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total scenarios: {len(scenarios)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    
    if failed == 0:
        print("\n🎉 All test scenarios passed!")
        print("\nKey validations confirmed:")
        print("✅ No infinite loops - built-in prevention works")
        print("✅ Parallel execution - significant speedup achieved")
        print("✅ Code reduction - implementation is much simpler")
        print("✅ State management - type-safe and corruption-free")
        print("✅ Advanced features - streaming and checkpointing work")
    else:
        print(f"\n⚠️  {failed} test scenarios failed. Check output above.")
    
    # Run quick coverage check
    print(f"\n{'='*60}")
    print("📈 Quick Coverage Check")
    print(f"{'='*60}")
    
    # Just check coverage for core modules
    run_command(
        "pytest tests/test_state.py tests/test_nodes.py --cov=src.state --cov=src.nodes --cov-report=term-missing --no-header -q",
        "Coverage for Core Modules"
    )
    
    print("\n💡 To run the full test suite:")
    print("   pytest")
    print("\n💡 To run with full coverage:")
    print("   pytest --cov=src --cov-report=html")
    print("\n💡 To run specific test categories:")
    print("   pytest -m unit      # Unit tests only")
    print("   pytest -m e2e       # End-to-end tests only")
    print("   pytest -m performance  # Performance tests only")


if __name__ == "__main__":
    main()