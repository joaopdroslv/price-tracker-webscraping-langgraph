import os

from dotenv import load_dotenv

load_dotenv()

PLAYWRIGHT_MCP_URL = os.getenv("PLAYWRIGHT_MCP_URL")
OPENAI_API_kEY = os.getenv("OPENAI_API_KEY")
