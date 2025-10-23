"""Test Agent SDK connection and configuration loading."""

import sys
from pathlib import Path

# Add parent directory to path to enable package imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config_loader import (
    load_secrets,
    load_user_preferences,
    get_anthropic_api_key,
    get_tavily_api_key
)
from src.utils.mock_clients import get_anthropic_client, is_mock_key


def test_load_secrets():
    """Test loading secrets.json."""
    print("\n=== Testing secrets loading ===")
    try:
        secrets = load_secrets()
        print("✓ secrets.json loaded successfully")
        print(f"  Found keys: {list(secrets.keys())}")
        return True
    except Exception as e:
        print(f"✗ Failed to load secrets: {e}")
        return False


def test_load_user_preferences():
    """Test loading user preferences YAML."""
    print("\n=== Testing user preferences loading ===")
    try:
        config = load_user_preferences()
        print("✓ user_preferences.yaml loaded successfully")
        print(f"  Topics configured: {len(config.get('topics', []))}")
        print(f"  Sources configured: {list(config.get('sources', {}).keys())}")
        print(f"  Output style: {config.get('output', {}).get('style', 'N/A')}")
        return True
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return False


def test_anthropic_api_key():
    """Test retrieving Anthropic API key."""
    print("\n=== Testing Anthropic API key ===")
    try:
        api_key = get_anthropic_api_key()
        if api_key and api_key.startswith("sk-ant-"):
            print("✓ Anthropic API key retrieved successfully")
            print(f"  Key prefix: {api_key[:20]}...")
            return True
        else:
            print("✗ Invalid Anthropic API key format")
            return False
    except Exception as e:
        print(f"✗ Failed to get API key: {e}")
        return False


def test_anthropic_connection():
    """Test connection to Anthropic API (or mock)."""
    print("\n=== Testing Anthropic API connection ===")
    try:
        api_key = get_anthropic_api_key()

        # Check if using mock
        if is_mock_key(api_key):
            print("  ⚠️  MOCK MODE: Using simulated API (no real calls)")
        else:
            print("  Using REAL Anthropic API")

        client = get_anthropic_client(api_key)

        # Send a simple test message
        print("  Sending test message to Claude...")
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello from the Intelligent News Aggregator test!' and nothing else."
                }
            ]
        )

        response_text = message.content[0].text
        print(f"✓ API connection successful!")
        print(f"  Response: {response_text}")
        print(f"  Tokens used: {message.usage.input_tokens} in, {message.usage.output_tokens} out")
        print(f"  Model: {message.model}")
        return True

    except Exception as e:
        print(f"✗ API connection failed: {e}")
        return False


def test_tavily_api_key():
    """Test retrieving Tavily API key (optional)."""
    print("\n=== Testing Tavily API key (optional) ===")
    try:
        api_key = get_tavily_api_key()
        if api_key and api_key.startswith("tvly-"):
            print("✓ Tavily API key retrieved successfully")
            print(f"  Key prefix: {api_key[:15]}...")
            return True
        else:
            print("⚠ Tavily API key not configured (optional for Phase 1)")
            return True  # Not required for Phase 1
    except Exception as e:
        print(f"✗ Failed to get Tavily API key: {e}")
        return True  # Not critical for Phase 1


def main():
    """Run all connection tests."""
    print("=" * 70)
    print("INTELLIGENT NEWS AGGREGATOR - Agent SDK Connection Test")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("Load secrets.json", test_load_secrets()))
    results.append(("Load user_preferences.yaml", test_load_user_preferences()))
    results.append(("Get Anthropic API key", test_anthropic_api_key()))
    results.append(("Anthropic API connection", test_anthropic_connection()))
    results.append(("Get Tavily API key (optional)", test_tavily_api_key()))

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
        print("\n🎉 All tests passed! Ready to begin development.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix configuration before continuing.")
        return 1


if __name__ == "__main__":
    exit(main())
