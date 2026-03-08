"""
Simple Strands Agent Example

This demonstrates a basic agent that can answer questions about geography
and use tools like calculator and HTTP requests.

Prerequisites:
1. Install: pip install strands-agents strands-agents-tools
2. Set up Bedrock API key: export AWS_BEDROCK_API_KEY=your_key
3. Enable model access in Bedrock console
"""

from strands import Agent
from strands_tools import calculator, http_request

# Create an agent with tools
agent = Agent(
    tools=[calculator, http_request],
    system_prompt="You are a helpful assistant that can perform calculations and fetch web data."
)

# Test the agent with a simple question
print("Testing agent with a calculation...")
response = agent("What is 15 * 23 + 47?")
print(f"Response: {response}\n")

# Test conversation memory
print("Testing conversation memory...")
agent("My favorite color is blue")
response = agent("What's my favorite color?")
print(f"Response: {response}\n")

print("Agent is ready! You can now interact with it.")
