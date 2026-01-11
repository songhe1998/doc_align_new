import os
from dotenv import load_dotenv

load_dotenv()

# API Key should be set in environment variables (e.g. .env file)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    # Fallback/Warning (optional, or just let it fail later if not present)
    pass

