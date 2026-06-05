"""Model client.

OpenRouter is OpenAI-compatible, so we use the OpenAI SDK and just swap the
base_url. Switching models is a one-line change (see part7_index.py).
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

MODEL = "openai/gpt-oss-120b:free"
