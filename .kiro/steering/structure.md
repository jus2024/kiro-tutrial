# Project Structure

## Current Organization

```
.
├── .kiro/              # Kiro AI assistant configuration
│   └── steering/       # AI guidance documents
└── .vscode/            # VS Code workspace settings
```

## Recommended Structure

### For AWS Serverless Applications

```
.
├── src/
│   ├── functions/           # Lambda function handlers
│   │   ├── api/            # API endpoint handlers
│   │   │   ├── users/
│   │   │   │   ├── get.ts
│   │   │   │   ├── post.ts
│   │   │   │   └── handler.test.ts
│   │   │   └── products/
│   │   ├── events/         # Event-driven handlers (SQS, SNS, etc.)
│   │   └── scheduled/      # EventBridge scheduled tasks
│   ├── layers/             # Lambda layers (shared code)
│   │   └── common/
│   │       ├── nodejs/     # Node.js layer
│   │       └── python/     # Python layer
│   ├── services/           # Business logic (reusable across functions)
│   ├── models/             # Data models and schemas
│   ├── repositories/       # Data access layer (DynamoDB, S3, etc.)
│   ├── middleware/         # Lambda middleware (auth, logging, etc.)
│   ├── utils/              # Helper functions
│   └── types/              # TypeScript type definitions
├── events/                 # Sample event payloads for testing
├── tests/                  # Integration and E2E tests
│   ├── integration/
│   └── e2e/
├── infrastructure/         # IaC definitions
│   ├── template.yaml      # SAM template
│   ├── cdk/               # CDK stacks (if using CDK)
│   └── serverless.yml     # Serverless Framework config
├── scripts/               # Deployment and utility scripts
└── docs/                  # Documentation
```

### Alternative: Monorepo Structure for Multiple Services

```
.
├── services/
│   ├── user-service/
│   │   ├── src/
│   │   ├── template.yaml
│   │   └── package.json
│   ├── product-service/
│   │   ├── src/
│   │   ├── template.yaml
│   │   └── package.json
│   └── shared/            # Shared code across services
│       └── layers/
├── infrastructure/        # Shared infrastructure
└── scripts/              # Deployment scripts
```

### For Web Applications (Frontend + Serverless Backend)
```
.
├── frontend/              # React/Vue/Next.js application
│   ├── src/
│   ├── public/
│   └── package.json
├── backend/               # Serverless backend
│   ├── src/
│   │   └── functions/
│   └── template.yaml
└── infrastructure/        # Shared infrastructure (S3, CloudFront, etc.)
```

## Conventions

### General
- Keep related files close together
- Use clear, descriptive folder names
- Separate concerns (handlers, business logic, data access)
- Co-locate tests with source files or in dedicated test directories
- Use index files for clean exports

### AWS Serverless Specific
- One Lambda function per file in `functions/` directory
- Group related functions by domain (users, products, orders, etc.)
- Keep Lambda handlers thin - delegate to service layer
- Store reusable code in layers or shared modules
- Name functions descriptively: `getUserById`, `createOrder`, `processPayment`
- Use consistent naming for API paths and function names
- Keep event schemas in separate files for reusability
- Document IAM permissions required for each function
