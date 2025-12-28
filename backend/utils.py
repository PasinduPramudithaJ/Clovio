import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def get_or_create_secret_key() -> str:
    """
    Get SECRET_KEY from environment or generate a new one.
    If no key exists, generates one and optionally saves to .env file.
    """
    secret_key = os.getenv("SECRET_KEY")
    
    # Check if secret key is missing or is a default/placeholder value
    default_placeholders = [
        "your-secret-key-change-in-production",
        "your-secret-key-here",
        "change-this-secret-key",
        "secret-key-here"
    ]
    
    if not secret_key or secret_key.lower() in [p.lower() for p in default_placeholders]:
        # Generate a new secret key
        secret_key = secrets.token_urlsafe(64)
        
        # Try to update .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            try:
                # Read existing .env file
                env_content = env_file.read_text()
                
                # Check if SECRET_KEY already exists in file
                if "SECRET_KEY=" in env_content:
                    # Replace existing SECRET_KEY
                    lines = env_content.split('\n')
                    updated_lines = []
                    for line in lines:
                        if line.strip().startswith("SECRET_KEY="):
                            updated_lines.append(f"SECRET_KEY={secret_key}")
                        else:
                            updated_lines.append(line)
                    env_file.write_text('\n'.join(updated_lines))
                else:
                    # Append SECRET_KEY if it doesn't exist
                    env_file.write_text(env_content + f"\nSECRET_KEY={secret_key}\n")
                
                print("[OK] Generated and saved SECRET_KEY to .env file")
            except Exception as e:
                print(f"[WARNING] Could not update .env file: {e}")
                print(f"[WARNING] Please manually add SECRET_KEY={secret_key} to your .env file")
        else:
            # Create new .env file
            try:
                env_file.write_text(f"SECRET_KEY={secret_key}\n")
                print("[OK] Generated and created .env file with SECRET_KEY")
            except Exception as e:
                print(f"[WARNING] Could not create .env file: {e}")
                print(f"[WARNING] Please create .env file and add: SECRET_KEY={secret_key}")
    
    return secret_key

