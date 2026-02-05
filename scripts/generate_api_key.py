#!/usr/bin/env python3
"""
Generate a secure API key for SearchSift.

Usage:
    python scripts/generate_api_key.py

The generated key should be:
1. Added to backend/config.py as API_KEY
2. Entered in the browser extension settings
"""

import secrets
import string


def generate_api_key(length: int = 32) -> str:
    """Generate a cryptographically secure API key."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def main():
    api_key = generate_api_key()

    print("\n" + "=" * 60)
    print("SearchSift API Key Generator")
    print("=" * 60)
    print(f"\nYour new API key:\n")
    print(f"    {api_key}")
    print(f"\n" + "-" * 60)
    print("\nNext steps:")
    print("\n1. Add to backend/config.py:")
    print(f'   API_KEY = "{api_key}"')
    print("\n2. Or set as environment variable:")
    print(f'   export SEARCHSIFT_API_KEY="{api_key}"')
    print("\n3. Enter the same key in the browser extension settings")
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
