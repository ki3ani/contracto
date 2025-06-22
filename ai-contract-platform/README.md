# AI Contract Intelligence Platform

An intelligent document analysis platform that uses AWS AI services to analyze contracts, identify risks, extract key terms, and detect missing clauses. Built with a serverless architecture using AWS Lambda, API Gateway, Step Functions, and powered by Amazon Bedrock (Claude 3), Textract, and Comprehend.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway    │    │   Lambda        │
│   (React +      │◄──►│   + Cognito      │◄──►│   Functions     │
│   TypeScript)   │    │   Auth           │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                ▲                        │
                                │                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EventBridge   │    │   Step Functions │    │   AI Services   │
│   (Notifications)│◄──►│   (Orchestration)│◄──►│   (Bedrock,     │
│                 │    │                  │    │   Textract,     │
└─────────────────┘    └──────────────────┘    │   Comprehend)   │
                                                └─────────────────┘
                               ▲                        │
                               │                        ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │   DynamoDB       │    │   S3 Bucket     │
                    │   (Metadata)     │    │   (Documents)   │
                    └──────────────────┘    └─────────────────┘
```

## 🚀 Features

- **Document Upload**: Secure upload of PDF/DOCX contracts with presigned URLs
- **Text Extraction**: OCR and text extraction using Amazon Textract
- **AI Analysis**: Contract analysis using Amazon Bedrock (Claude 3)
- **Risk Assessment**: Automated risk scoring and identification
- **Key Terms Extraction**: Identification of important contract terms
- **Missing Clauses Detection**: Detection of standard missing clauses
- **Real-time Notifications**: EventBridge-powered notifications
- **User Authentication**: Cognito-based authentication and authorization
- **RESTful API**: Complete API for contract management
- **Serverless Architecture**: Cost-effective and scalable

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- AWS SAM CLI installed
- Python 3.11+
- Node.js 18+ (for frontend)
- Docker (for SAM local development)

## 🛠️ Installation & Setup

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ai-contract-platform

# Setup development environment
make setup-dev

# Install dependencies
make install
```

### 2. Configure AWS Resources

```bash
# Initialize SAM configuration
make init-config

# Validate the template
make validate
```

### 3. Deploy to Development

```bash
# Build and deploy to dev environment
make dev-deploy

# Or deploy to specific environment
make deploy ENV=staging
```

## 📁 Project Structure

```
ai-contract-platform/
├── backend/
│   ├── src/
│   │   ├── functions/           # Lambda functions
│   │   │   ├── document_upload/ # Document upload handler
│   │   │   ├── text_extraction/ # Textract integration
│   │   │   ├── ai_analysis/     # Bedrock analysis
│   │   │   └── api_handler/     # API endpoints
│   │   ├── layers/
│   │   │   └── common/          # Shared utilities
│   │   ├── shared/              # Shared resources
│   │   └── step_functions/      # Step function definitions
│   └── tests/                   # Backend tests
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API services
│   │   ├── utils/               # Utilities
│   │   └── types/               # TypeScript types
│   └── public/                  # Static assets
├── scripts/                     # Deployment scripts
├── docs/                        # Documentation
├── template.yaml                # SAM template
├── Makefile                     # Build automation
└── README.md                    # This file
```

## 🔧 Development

### Available Commands

```bash
# Development
make help              # Show available commands
make install          # Install all dependencies
make build            # Build SAM application
make validate         # Validate SAM template
make test             # Run tests
make lint             # Run linting
make format           # Format code

# Deployment
make deploy-dev       # Deploy to development
make deploy-staging   # Deploy to staging
make deploy-prod      # Deploy to production
make deploy ENV=<env> # Deploy to specific environment

# Local Development
make local-api        # Start local API Gateway
make local-invoke FUNCTION=<name>  # Invoke function locally

# Monitoring
make logs FUNCTION=<name>  # Tail function logs
make tail-logs        # Tail all logs
make describe         # Describe deployed stack

# Cleanup
make clean            # Clean build artifacts
```

### Local Development

```bash
# Start local API Gateway
make local-api

# The API will be available at: http://localhost:3001

# Test individual functions
make local-invoke FUNCTION=DocumentUploadFunction
```

### Environment Configuration

The platform supports multiple environments (dev, staging, prod). Each environment has its own:
- CloudFormation stack
- S3 buckets
- DynamoDB tables
- Cognito user pools

## 📡 API Endpoints

### Authentication
All endpoints require AWS Cognito authentication via JWT tokens.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload contract document |
| GET | `/contracts` | List user contracts |
| GET | `/contracts/{id}` | Get contract details |
| GET | `/contracts/{id}/analysis` | Get contract analysis |

### Example Usage

```bash
# Upload a contract
curl -X POST https://your-api-endpoint/upload \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "contract.pdf",
    "file_size": 1024000,
    "content_type": "application/pdf"
  }'

# List contracts
curl -H "Authorization: Bearer <jwt-token>" \
  https://your-api-endpoint/contracts

# Get contract analysis
curl -H "Authorization: Bearer <jwt-token>" \
  https://your-api-endpoint/contracts/{contract-id}/analysis
```

## 🤖 AI Analysis Features

### Contract Analysis (Amazon Bedrock)
- Risk identification and assessment
- Key terms extraction
- Missing clauses detection
- Unusual provisions identification
- Compliance issues detection
- Recommendations for improvement

### Text Processing (Amazon Textract)
- OCR for PDF documents
- Text extraction from DOCX files
- Page count and confidence scoring
- Support for large documents via asynchronous processing

### Language Analysis (Amazon Comprehend)
- Sentiment analysis
- Entity extraction (persons, organizations, locations)
- Key phrase extraction

## 🔒 Security Features

- **Authentication**: AWS Cognito user pools
- **Authorization**: JWT token validation
- **Data Encryption**: S3 server-side encryption
- **Access Control**: IAM roles with least privilege
- **API Security**: CORS configuration and rate limiting
- **Data Privacy**: User data isolation

## 📊 Monitoring & Logging

### CloudWatch Integration
- Structured JSON logging
- Request tracing with correlation IDs
- Performance metrics
- Error tracking

### Log Analysis
```bash
# View logs for specific function
make logs FUNCTION=DocumentUploadFunction

# Tail all function logs
make tail-logs
```

## 💰 Cost Optimization

- **Serverless Architecture**: Pay only for what you use
- **Lambda Provisioned Concurrency**: Optional for production workloads
- **S3 Lifecycle Policies**: Automatic cleanup of old documents
- **DynamoDB On-Demand**: Scales automatically with usage

## 🚀 Deployment Guide

### Development Environment
```bash
make deploy-dev
```

### Staging Environment
```bash
make deploy-staging
```

### Production Environment
```bash
# Production deployment requires confirmation
make deploy-prod
```

### CI/CD Integration
The Makefile commands can be integrated into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Deploy to Staging
  run: make deploy-staging
  
- name: Run Tests
  run: make test
```

## 🔧 Configuration

### Environment Variables
Key environment variables used by the Lambda functions:

- `DOCUMENTS_BUCKET`: S3 bucket for document storage
- `METADATA_TABLE`: DynamoDB table for contract metadata
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `BEDROCK_MODEL_ID`: Bedrock model identifier

### AWS Permissions
The Lambda functions require the following AWS permissions:
- S3: Read/Write access to documents bucket
- DynamoDB: Read/Write access to metadata table
- Textract: Document analysis permissions
- Bedrock: Model invocation permissions
- Comprehend: Text analysis permissions
- Step Functions: Execution permissions
- EventBridge: Event publishing permissions

## 🐛 Troubleshooting

### Common Issues

1. **SAM Build Failures**
   ```bash
   make clean
   make build
   ```

2. **Permission Errors**
   - Verify AWS credentials are configured
   - Check IAM permissions for the deployment user

3. **Local Development Issues**
   ```bash
   # Ensure Docker is running for SAM local
   docker --version
   
   # Check SAM CLI version
   sam --version
   ```

4. **Function Timeout Errors**
   - Increase Lambda timeout in template.yaml
   - Check CloudWatch logs for specific error details

### Debug Mode
Enable debug logging by setting `LOG_LEVEL=DEBUG` in the environment variables.

## 📈 Performance Tuning

### Lambda Optimization
- Adjust memory allocation based on usage patterns
- Enable provisioned concurrency for consistent performance
- Use Lambda layers for shared dependencies

### Database Optimization
- Configure DynamoDB auto-scaling
- Use appropriate GSI design for query patterns
- Monitor read/write capacity utilization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review CloudWatch logs
3. Open an issue in the repository

## 🔄 Roadmap

- [ ] Frontend React application
- [ ] Real-time WebSocket notifications
- [ ] Advanced contract comparison features
- [ ] Multi-language support
- [ ] Integration with popular contract management systems
- [ ] Advanced analytics dashboard
- [ ] Batch processing capabilities