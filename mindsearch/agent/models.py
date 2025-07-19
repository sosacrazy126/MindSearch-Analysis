import os
import sys

from dotenv import load_dotenv
from lagent.llms import GPTAPI

# Load environment variables from .env file
load_dotenv()

# Check for OpenAI API key in environment variables
openai_api_key = os.environ.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables.")
    print("Please set your OpenAI API key using: export OPENAI_API_KEY='your-api-key'")
    openai_api_key = "YOUR OPENAI API KEY"

# openai_api_base needs to fill in the complete chat api address, such as: https://api.openai.com/v1/chat/completions
gpt4 = dict(
    type=GPTAPI,
    model_type="gpt-4-turbo",
    key=openai_api_key,
    api_base=os.environ.get("OPENAI_API_BASE") or os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1/chat/completions",
)

