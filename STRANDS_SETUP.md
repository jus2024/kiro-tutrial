# Strands Agent Setup Guide

## Quick Start (3 Steps)

### 1. Install Required Packages

```bash
# For Amazon Bedrock (default, recommended)
pip install strands-agents strands-agents-tools

# Or for other providers:
# pip install 'strands-agents[anthropic]' strands-agents-tools  # Anthropic Claude
# pip install 'strands-agents[openai]' strands-agents-tools     # OpenAI GPT
# pip install 'strands-agents[gemini]' strands-agents-tools     # Google Gemini
```

### 2. Get API Key (Bedrock)

**Option A: Quick Start with Bedrock API Key (Development)**
1. Open [Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Navigate to "API keys" in the left sidebar
3. Click "Generate long-term API key" (valid for 30 days)
4. Copy and save the key securely (shown only once!)
5. Set environment variable:
   ```bash
   export AWS_BEDROCK_API_KEY=your_bedrock_api_key
   ```

**Option B: AWS Credentials (Production)**
```bash
aws configure
# Or set manually:
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-west-2
```

### 3. Enable Model Access

1. Open [Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Click "Model access" in left sidebar
3. Click "Manage model access"
4. Enable "Claude 4 Sonnet" (or your preferred model)
5. Wait a few minutes for access to propagate

## Run the Example

```bash
python simple_agent.py
```

## Next Steps

Check out the example file `simple_agent.py` to see how to:
- Create an agent with tools
- Ask questions and get responses
- Use conversation memory

## Troubleshooting

**"Access denied to model"**
- Enable model access in Bedrock console (see step 3 above)

**"Invalid API key"**
- Verify: `echo $AWS_BEDROCK_API_KEY`
- Regenerate key if expired (30-day limit)

**"Module not found"**
- Run: `pip install strands-agents strands-agents-tools`
