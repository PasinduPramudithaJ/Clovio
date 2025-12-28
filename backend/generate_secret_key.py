#!/usr/bin/env python3
"""
Utility script to generate a secure secret key for JWT signing.
Run this script to generate a new secret key.
"""

import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def generate_secret_key():
    """Generate a new secret key and optionally save it to .env file."""
    secret_key = secrets.token_urlsafe(64)
    
    print("=" * 60)
    print("Generated Secret Key:")
    print("=" * 60)
    print(secret_key)
    print("=" * 60)
    
    # Ask if user wants to save to .env
    env_file = Path(".env")
    
    if env_file.exists():
        # Read existing content
        env_content = env_file.read_text()
        
        if "SECRET_KEY=" in env_content:
            # Update existing SECRET_KEY
            lines = env_content.split('\n')
            updated_lines = []
            updated = False
            for line in lines:
                if line.startswith("SECRET_KEY="):
                    updated_lines.append(f"SECRET_KEY={secret_key}")
                    updated = True
                else:
                    updated_lines.append(line)
            
            if updated:
                env_file.write_text('\n'.join(updated_lines))
                print("\n[OK] Updated SECRET_KEY in .env file")
            else:
                env_file.write_text(env_content + f"\nSECRET_KEY={secret_key}\n")
                print("\n[OK] Added SECRET_KEY to .env file")
        else:
            # Append SECRET_KEY
            env_file.write_text(env_content + f"\nSECRET_KEY={secret_key}\n")
            print("\n[OK] Added SECRET_KEY to .env file")
    else:
        # Create new .env file
        env_file.write_text(f"SECRET_KEY={secret_key}\n")
        print("\n[OK] Created .env file with SECRET_KEY")
    
    print("\nYou can now use this key in your application.")
    print("The key has been automatically saved to your .env file.\n")


if __name__ == "__main__":
    generate_secret_key()

