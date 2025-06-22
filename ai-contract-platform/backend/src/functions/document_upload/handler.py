import json
import os
import boto3
from typing import Dict, Any
from common.logger import get_logger, log_with_context
from common.utils import (
    generate_contract_id, 
    generate_timestamp, 
    create_api_response, 
    create_error_response,
    extract_user_id_from_event,
    validate_contract_metadata
)
from common.exceptions import ValidationError, DocumentUploadError, DatabaseError

logger = get_logger(__name__)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
stepfunctions_client = boto3.client('stepfunctions')

# Environment variables
DOCUMENTS_BUCKET = os.environ['DOCUMENTS_BUCKET']
METADATA_TABLE = os.environ['METADATA_TABLE']
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')

table = dynamodb.Table(METADATA_TABLE)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle document upload requests"""
    request_id = context.aws_request_id
    
    try:
        logger.info("Starting document upload", extra={'request_id': request_id})
        
        # Extract user ID from the event
        user_id = extract_user_id_from_event(event)
        if not user_id:
            raise ValidationError("User authentication required")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        validate_contract_metadata(body)
        
        # Generate contract ID and timestamp
        contract_id = generate_contract_id()
        timestamp = generate_timestamp()
        
        log_with_context(
            logger, 'info', 
            "Processing document upload",
            contract_id=contract_id,
            user_id=user_id,
            request_id=request_id
        )
        
        # Create S3 key
        s3_key = f"contracts/{user_id}/{contract_id}/{body['filename']}"
        
        # Generate presigned URL for upload
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': DOCUMENTS_BUCKET,
                'Key': s3_key,
                'ContentType': body['content_type']
            },
            ExpiresIn=3600  # 1 hour
        )
        
        # Store metadata in DynamoDB
        metadata = {
            'contract_id': contract_id,
            'user_id': user_id,
            'filename': body['filename'],
            'file_size': body['file_size'],
            'content_type': body['content_type'],
            's3_key': s3_key,
            'status': 'uploaded',
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        try:
            table.put_item(Item=metadata)
            logger.info(
                "Metadata stored successfully",
                extra={
                    'contract_id': contract_id,
                    'user_id': user_id,
                    'request_id': request_id
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to store metadata: {str(e)}",
                extra={
                    'contract_id': contract_id,
                    'user_id': user_id,
                    'request_id': request_id
                }
            )
            raise DatabaseError("Failed to store contract metadata")
        
        # Start Step Functions execution if configured
        if STATE_MACHINE_ARN:
            try:
                stepfunctions_client.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    name=f"contract-{contract_id}",
                    input=json.dumps({
                        'contract_id': contract_id,
                        's3_bucket': DOCUMENTS_BUCKET,
                        's3_key': s3_key
                    })
                )
                logger.info(
                    "Step Functions execution started",
                    extra={
                        'contract_id': contract_id,
                        'user_id': user_id,
                        'request_id': request_id
                    }
                )
            except Exception as e:
                logger.warning(
                    f"Failed to start Step Functions execution: {str(e)}",
                    extra={
                        'contract_id': contract_id,
                        'user_id': user_id,
                        'request_id': request_id
                    }
                )
        
        response_body = {
            'contract_id': contract_id,
            'upload_url': presigned_url,
            'status': 'upload_ready'
        }
        
        logger.info(
            "Document upload processed successfully",
            extra={
                'contract_id': contract_id,
                'user_id': user_id,
                'request_id': request_id
            }
        )
        
        return create_api_response(201, response_body)
        
    except ValidationError as e:
        logger.warning(f"Validation error: {str(e)}", extra={'request_id': request_id})
        return create_error_response(e, request_id)
    except DocumentUploadError as e:
        logger.error(f"Document upload error: {str(e)}", extra={'request_id': request_id})
        return create_error_response(e, request_id)
    except DatabaseError as e:
        logger.error(f"Database error: {str(e)}", extra={'request_id': request_id})
        return create_error_response(e, request_id)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", extra={'request_id': request_id})
        return create_error_response(e, request_id)