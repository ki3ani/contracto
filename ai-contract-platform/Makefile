# AI Contract Intelligence Platform - Makefile
# Available commands for development and deployment

.PHONY: help install build test deploy clean lint format validate deploy-dev deploy-staging deploy-prod logs

# Default environment
ENV ?= dev

# Colors for output
GREEN=\033[0;32m
YELLOW=\033[1;33m
RED=\033[0;31m
NC=\033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)AI Contract Intelligence Platform$(NC)"
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies for all components
	@echo "$(GREEN)Installing dependencies...$(NC)"
	# Backend dependencies
	@for func in document_upload text_extraction ai_analysis api_handler; do \
		echo "Installing dependencies for $$func..."; \
		cd backend/src/functions/$$func && pip install -r requirements.txt -t .; \
		cd -; \
	done
	# Common layer dependencies
	cd backend/src/layers/common && pip install -r requirements.txt -t python/
	# Frontend dependencies (if package.json exists)
	@if [ -f frontend/package.json ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi

build: ## Build the SAM application
	@echo "$(GREEN)Building SAM application...$(NC)"
	sam build --use-container --parallel

validate: ## Validate SAM template
	@echo "$(GREEN)Validating SAM template...$(NC)"
	sam validate --lint

test: ## Run tests
	@echo "$(GREEN)Running tests...$(NC)"
	# Backend tests
	@if [ -d backend/tests ]; then \
		cd backend && python -m pytest tests/ -v; \
	else \
		echo "$(YELLOW)No backend tests found$(NC)"; \
	fi
	# Frontend tests
	@if [ -f frontend/package.json ]; then \
		cd frontend && npm test; \
	else \
		echo "$(YELLOW)No frontend tests configured$(NC)"; \
	fi

lint: ## Run linting
	@echo "$(GREEN)Running linting...$(NC)"
	# Python linting
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 backend/src/ --max-line-length=120 --ignore=E501,W503; \
	else \
		echo "$(YELLOW)flake8 not installed, skipping Python linting$(NC)"; \
	fi
	# Frontend linting
	@if [ -f frontend/package.json ]; then \
		cd frontend && npm run lint; \
	fi

format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	# Python formatting
	@if command -v black >/dev/null 2>&1; then \
		black backend/src/ --line-length=120; \
	else \
		echo "$(YELLOW)black not installed, skipping Python formatting$(NC)"; \
	fi
	# Frontend formatting
	@if [ -f frontend/package.json ]; then \
		cd frontend && npm run format; \
	fi

deploy-dev: ENV=dev
deploy-dev: ## Deploy to development environment
	@echo "$(GREEN)Deploying to development environment...$(NC)"
	sam deploy --config-env dev --parameter-overrides Environment=dev

deploy-staging: ENV=staging
deploy-staging: ## Deploy to staging environment
	@echo "$(GREEN)Deploying to staging environment...$(NC)"
	sam deploy --config-env staging --parameter-overrides Environment=staging

deploy-prod: ENV=prod
deploy-prod: ## Deploy to production environment
	@echo "$(GREEN)Deploying to production environment...$(NC)"
	@echo "$(RED)WARNING: Deploying to production!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	sam deploy --config-env prod --parameter-overrides Environment=prod

deploy: ## Deploy to specified environment (default: dev)
	@echo "$(GREEN)Deploying to $(ENV) environment...$(NC)"
	sam deploy --config-env $(ENV) --parameter-overrides Environment=$(ENV)

local-api: ## Start local API Gateway
	@echo "$(GREEN)Starting local API Gateway...$(NC)"
	sam local start-api --port 3001

local-invoke: ## Invoke function locally (requires FUNCTION parameter)
ifndef FUNCTION
	@echo "$(RED)Error: FUNCTION parameter required$(NC)"
	@echo "Usage: make local-invoke FUNCTION=DocumentUploadFunction"
	@exit 1
endif
	@echo "$(GREEN)Invoking $(FUNCTION) locally...$(NC)"
	sam local invoke $(FUNCTION) --event events/$(FUNCTION).json

logs: ## Tail CloudWatch logs (requires FUNCTION parameter)
ifndef FUNCTION
	@echo "$(RED)Error: FUNCTION parameter required$(NC)"
	@echo "Usage: make logs FUNCTION=DocumentUploadFunction"
	@exit 1
endif
	@echo "$(GREEN)Tailing logs for $(FUNCTION)...$(NC)"
	sam logs -n $(FUNCTION) --stack-name ai-contract-platform-$(ENV) --tail

describe: ## Describe the deployed stack
	@echo "$(GREEN)Describing stack...$(NC)"
	aws cloudformation describe-stacks --stack-name ai-contract-platform-$(ENV) --query 'Stacks[0].Outputs'

clean: ## Clean build artifacts
	@echo "$(GREEN)Cleaning build artifacts...$(NC)"
	rm -rf .aws-sam/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	# Clean function dependencies
	@for func in document_upload text_extraction ai_analysis api_handler; do \
		cd backend/src/functions/$$func && find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true; \
		cd -; \
	done

setup-dev: ## Setup development environment
	@echo "$(GREEN)Setting up development environment...$(NC)"
	# Install Python development dependencies
	pip install black flake8 pytest boto3 moto
	# Create sample event files
	mkdir -p events
	@echo '{"body": "{\"filename\": \"test.pdf\", \"file_size\": 1024, \"content_type\": \"application/pdf\"}", "requestContext": {"authorizer": {"claims": {"sub": "test-user-id"}}}}' > events/DocumentUploadFunction.json
	@echo "$(GREEN)Development environment setup complete!$(NC)"

package: ## Package the application for deployment
	@echo "$(GREEN)Packaging application...$(NC)"
	sam build
	sam package --s3-bucket contract-platform-deployment-$(ENV) --output-template-file packaged-template.yaml

init-config: ## Initialize SAM configuration files
	@echo "$(GREEN)Initializing SAM configuration...$(NC)"
	mkdir -p .aws-sam
	@echo 'version = 0.1' > samconfig.toml
	@echo '[default]' >> samconfig.toml
	@echo '[default.deploy]' >> samconfig.toml
	@echo '[default.deploy.parameters]' >> samconfig.toml
	@echo 'stack_name = "ai-contract-platform-dev"' >> samconfig.toml
	@echo 's3_bucket = "contract-platform-deployment-dev"' >> samconfig.toml
	@echo 'region = "us-east-1"' >> samconfig.toml
	@echo 'capabilities = "CAPABILITY_IAM"' >> samconfig.toml
	@echo 'parameter_overrides = "Environment=dev"' >> samconfig.toml
	@echo '' >> samconfig.toml
	@echo '[staging]' >> samconfig.toml
	@echo '[staging.deploy]' >> samconfig.toml
	@echo '[staging.deploy.parameters]' >> samconfig.toml
	@echo 'stack_name = "ai-contract-platform-staging"' >> samconfig.toml
	@echo 's3_bucket = "contract-platform-deployment-staging"' >> samconfig.toml
	@echo 'parameter_overrides = "Environment=staging"' >> samconfig.toml
	@echo '' >> samconfig.toml
	@echo '[prod]' >> samconfig.toml
	@echo '[prod.deploy]' >> samconfig.toml
	@echo '[prod.deploy.parameters]' >> samconfig.toml
	@echo 'stack_name = "ai-contract-platform-prod"' >> samconfig.toml
	@echo 's3_bucket = "contract-platform-deployment-prod"' >> samconfig.toml
	@echo 'parameter_overrides = "Environment=prod"' >> samconfig.toml

# Development workflow shortcuts
dev-deploy: build deploy-dev ## Build and deploy to dev environment

quick-deploy: ## Quick deploy without build (use with caution)
	@echo "$(YELLOW)Quick deploying to $(ENV) environment...$(NC)"
	sam deploy --config-env $(ENV) --parameter-overrides Environment=$(ENV)

# Monitoring and debugging
tail-logs: ## Tail all function logs
	@echo "$(GREEN)Tailing all function logs...$(NC)"
	sam logs --stack-name ai-contract-platform-$(ENV) --tail

sync: ## Sync code changes for faster development (SAM CLI 1.50+)
	@echo "$(GREEN)Syncing code changes...$(NC)"
	sam sync --stack-name ai-contract-platform-$(ENV) --watch