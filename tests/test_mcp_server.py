"""Test MCP server functionality."""

import sys
from pathlib import Path
import asyncio

# Add parent directory to path to enable package imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_servers import (
    create_claude_haiku_server,
    create_claude_sonnet_server,
    get_tier1_server,
    get_tier2_server
)


async def test_haiku_server():
    """Test Haiku MCP server (Tier 1)."""
    print("\n=== Testing Claude Haiku MCP Server (Tier 1) ===")
    try:
        server = create_claude_haiku_server()
        print(f"✓ Created server: {server}")
        print(f"  Model: {server.model}")
        print(f"  Tier: {server.get_tier_name()}")

        # Test completion
        print("\n  Testing completion...")
        response = await server.complete(
            prompt="What is 2+2? Answer with just the number.",
            max_tokens=10,
            temperature=0.0
        )

        print(f"✓ Completion successful!")
        print(f"  Response: {response.content[:100]}")
        print(f"  Tokens: {response.input_tokens} in, {response.output_tokens} out")
        print(f"  Cost: ${response.cost_usd:.6f}")
        print(f"  Time: {response.response_time_seconds:.2f}s")
        print(f"  Is mock: {response.metadata.get('is_mock', False)}")

        # Check stats
        stats = server.get_stats()
        print(f"\n  Server stats:")
        print(f"    Requests: {stats['request_count']}")
        print(f"    Total tokens: {stats['total_tokens']}")
        print(f"    Total cost: ${stats['total_cost_usd']:.6f}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_sonnet_server():
    """Test Sonnet MCP server (Tier 2)."""
    print("\n=== Testing Claude Sonnet MCP Server (Tier 2) ===")
    try:
        server = create_claude_sonnet_server()
        print(f"✓ Created server: {server}")
        print(f"  Model: {server.model}")
        print(f"  Tier: {server.get_tier_name()}")

        # Test completion with system prompt
        print("\n  Testing completion with system prompt...")
        response = await server.complete(
            prompt="Explain why Python is popular for data science in one sentence.",
            max_tokens=50,
            temperature=0.7,
            system_prompt="You are a helpful technical assistant."
        )

        print(f"✓ Completion successful!")
        print(f"  Response: {response.content[:150]}")
        print(f"  Tokens: {response.input_tokens} in, {response.output_tokens} out")
        print(f"  Cost: ${response.cost_usd:.6f}")
        print(f"  Time: {response.response_time_seconds:.2f}s")

        # Check stats
        stats = server.get_stats()
        print(f"\n  Server stats:")
        print(f"    Requests: {stats['request_count']}")
        print(f"    Total cost: ${stats['total_cost_usd']:.6f}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tier_helpers():
    """Test tier helper functions."""
    print("\n=== Testing Tier Helper Functions ===")
    try:
        tier1 = get_tier1_server()
        tier2 = get_tier2_server()

        print(f"✓ Tier 1 server: {tier1.model}")
        print(f"✓ Tier 2 server: {tier2.model}")

        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def main():
    """Run all MCP server tests."""
    print("=" * 70)
    print("MCP SERVER TESTS")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("Haiku Server (Tier 1)", await test_haiku_server()))
    results.append(("Sonnet Server (Tier 2)", await test_sonnet_server()))
    results.append(("Tier Helper Functions", await test_tier_helpers()))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All MCP server tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed.")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
