"""Main entry point for Intelligent News Aggregator."""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator.main_orchestrator import MainOrchestrator
from src.utils.config_loader import load_user_preferences


async def main():
    """Run the intelligent news aggregator."""
    try:
        # Load preferences
        print("Loading user preferences...")
        preferences = load_user_preferences()

        # Create orchestrator
        orchestrator = MainOrchestrator(preferences)

        # Generate digest
        digest_path = await orchestrator.generate_digest()

        print(f"\n✓ Success! Read your digest at: {digest_path}\n")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
