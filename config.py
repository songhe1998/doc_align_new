import os
from dotenv import load_dotenv

# Debug info
print(f"DEBUG: Current CWD: {os.getcwd()}")
print(f"DEBUG: .env exists? {os.path.exists('.env')}")

load_dotenv()

# API Key should be set in environment variables (e.g. .env file)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print(f"DEBUG: Loaded API Key? {'Yes' if OPENAI_API_KEY else 'No'}")

if not OPENAI_API_KEY:
    # Fallback/Warning (optional, or just let it fail later if not present)
    pass

