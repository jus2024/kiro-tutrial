# Technology Stack

## Development Environment

- IDE: VS Code with Kiro AI assistant integration
- MCP (Model Context Protocol): Enabled for enhanced AI capabilities
- AWS CLI: For AWS resource management
- AWS SAM CLI / Serverless Framework: For local testing and deployment

## Tech Stack

### AWS Serverless Architecture

- **Compute**: AWS Lambda (Node.js/TypeScript or Python runtime)
- **API**: Amazon API Gateway (REST or HTTP APIs)
- **Storage**: Amazon S3 for static assets and file storage
- **Database**: Amazon DynamoDB for NoSQL data
- **Authentication**: Amazon Cognito for user management
- **Messaging**: Amazon SQS/SNS for async processing
- **Monitoring**: Amazon CloudWatch for logs and metrics
- **IaC**: AWS SAM, CDK, or Serverless Framework for infrastructure as code

## Build & Development Commands

### AWS SAM
```bash
# Install dependencies
npm install  # or pip install -r requirements.txt

# Build Lambda functions
sam build

# Run API locally
sam local start-api

# Invoke Lambda function locally
sam local invoke FunctionName -e events/event.json

# Deploy to AWS
sam deploy --guided

# Run tests
npm test  # or pytest
```

### Serverless Framework
```bash
# Install dependencies
npm install

# Deploy to AWS
serverless deploy

# Invoke function
serverless invoke -f functionName

# View logs
serverless logs -f functionName -t

# Run offline (local development)
serverless offline
```

### AWS CDK
```bash
# Install dependencies
npm install

# Synthesize CloudFormation template
cdk synth

# Deploy stack
cdk deploy

# Destroy stack
cdk destroy
```

## Dependencies

### Common AWS Serverless Dependencies

**Node.js/TypeScript:**
- `aws-sdk` or `@aws-sdk/client-*` - AWS SDK v3 (modular)
- `@types/aws-lambda` - Lambda type definitions
- `middy` - Middleware engine for Lambda
- `aws-lambda-powertools` - Utilities for Lambda best practices

**Python:**
- `boto3` - AWS SDK for Python
- `aws-lambda-powertools` - Python utilities for Lambda
- `pydantic` - Data validation

**Development:**
- `aws-sam-cli` - SAM CLI for local testing
- `serverless` - Serverless Framework
- `aws-cdk` - AWS CDK for IaC

## AWS Serverless Best Practices

### Lambda Function Design
- Keep functions small and focused (single responsibility)
- Use environment variables for configuration
- Implement proper error handling and retries
- Set appropriate timeout and memory settings
- Use Lambda layers for shared dependencies
- Minimize cold start impact (keep deployment package small)

### API Gateway
- Use API Gateway caching when appropriate
- Implement request validation at API Gateway level
- Use Lambda proxy integration for flexibility
- Enable CORS properly for web applications

### DynamoDB
- Design partition keys to avoid hot partitions
- Use GSI (Global Secondary Index) for alternative query patterns
- Implement single-table design when appropriate
- Use DynamoDB Streams for event-driven architectures

### Security
- Follow principle of least privilege for IAM roles
- Use AWS Secrets Manager or Parameter Store for sensitive data
- Enable AWS WAF for API Gateway when needed
- Implement proper authentication/authorization (Cognito, Lambda authorizers)
- Use VPC when accessing private resources

### Monitoring & Logging
- Use structured logging (JSON format)
- Implement distributed tracing with X-Ray
- Set up CloudWatch alarms for critical metrics
- Use CloudWatch Insights for log analysis
- Monitor Lambda concurrent executions and throttles

### Cost Optimization
- Right-size Lambda memory allocation
- Use provisioned concurrency only when necessary
- Implement lifecycle policies for S3
- Use DynamoDB on-demand pricing for unpredictable workloads
- Clean up unused resources regularly
