import json
import os
import boto3
from typing import Dict, Any, List
from common.logger import get_logger, log_with_context
from common.exceptions import TextExtractionError, DatabaseError
from common.utils import generate_timestamp

logger = get_logger(__name__)

# Initialize AWS clients
s3_client = boto3.client('s3')
textract_client = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')

# Environment variables
DOCUMENTS_BUCKET = os.environ['DOCUMENTS_BUCKET']
METADATA_TABLE = os.environ['METADATA_TABLE']

table = dynamodb.Table(METADATA_TABLE)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Extract text from uploaded documents using Amazon Textract"""
    request_id = context.aws_request_id
    contract_id = event.get('contract_id')
    s3_key = event.get('s3_key')
    
    try:
        log_with_context(
            logger, 'info',
            "Starting text extraction",
            contract_id=contract_id,
            request_id=request_id
        )
        
        # Update status to processing
        update_contract_status(contract_id, 'processing_text_extraction')
        
        # Determine if we need synchronous or asynchronous processing
        # For large documents, use asynchronous processing
        try:
            s3_response = s3_client.head_object(Bucket=DOCUMENTS_BUCKET, Key=s3_key)
            file_size = s3_response['ContentLength']
            
            if file_size > 5 * 1024 * 1024:  # 5MB threshold
                # Use asynchronous processing for large files
                extracted_text, page_count, confidence = extract_text_async(s3_key)
            else:
                # Use synchronous processing for smaller files
                extracted_text, page_count, confidence = extract_text_sync(s3_key)
                
        except Exception as e:
            logger.error(
                f"Failed to process document: {str(e)}",
                extra={'contract_id': contract_id, 'request_id': request_id}
            )
            raise TextExtractionError(f"Failed to extract text from document: {str(e)}")
        
        # Store extracted text in DynamoDB
        timestamp = generate_timestamp()
        try:
            table.update_item(
                Key={'contract_id': contract_id},
                UpdateExpression='SET extracted_text = :text, page_count = :pages, extraction_confidence = :conf, #status = :status, updated_at = :timestamp',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':text': extracted_text,
                    ':pages': page_count,
                    ':conf': confidence,
                    ':status': 'text_extracted',
                    ':timestamp': timestamp
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to update contract metadata: {str(e)}",
                extra={'contract_id': contract_id, 'request_id': request_id}
            )
            raise DatabaseError("Failed to update contract metadata")
        
        log_with_context(
            logger, 'info',
            f"Text extraction completed successfully. Pages: {page_count}, Confidence: {confidence}",
            contract_id=contract_id,
            request_id=request_id
        )
        
        return {
            'contract_id': contract_id,
            'extracted_text': extracted_text,
            'page_count': page_count,
            'extraction_confidence': confidence,
            'status': 'text_extracted'
        }
        
    except Exception as e:
        logger.error(
            f"Text extraction failed: {str(e)}",
            extra={'contract_id': contract_id, 'request_id': request_id}
        )
        
        # Update status to failed
        try:
            update_contract_status(contract_id, 'text_extraction_failed')
        except:
            pass  # Don't fail if status update fails
        
        raise e

def extract_text_sync(s3_key: str) -> tuple[str, int, float]:
    """Extract text using synchronous Textract processing"""
    try:
        response = textract_client.detect_document_text(
            Document={
                'S3Object': {
                    'Bucket': DOCUMENTS_BUCKET,
                    'Name': s3_key
                }
            }
        )
        
        # Extract text from response
        text_blocks = []
        confidence_scores = []
        
        for block in response['Blocks']:
            if block['BlockType'] == 'LINE':
                text_blocks.append(block['Text'])
                confidence_scores.append(block['Confidence'])
        
        extracted_text = '\n'.join(text_blocks)
        page_count = len(set(block.get('Page', 1) for block in response['Blocks'] if 'Page' in block))
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return extracted_text, page_count, avg_confidence
        
    except Exception as e:
        raise TextExtractionError(f"Synchronous text extraction failed: {str(e)}")

def extract_text_async(s3_key: str) -> tuple[str, int, float]:
    """Extract text using asynchronous Textract processing"""
    try:
        # Start document analysis
        response = textract_client.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': DOCUMENTS_BUCKET,
                    'Name': s3_key
                }
            }
        )
        
        job_id = response['JobId']
        
        # Poll for completion
        import time
        max_attempts = 60  # 5 minutes max
        attempt = 0
        
        while attempt < max_attempts:
            result = textract_client.get_document_text_detection(JobId=job_id)
            status = result['JobStatus']
            
            if status == 'SUCCEEDED':
                break
            elif status == 'FAILED':
                raise TextExtractionError("Textract job failed")
            
            time.sleep(5)  # Wait 5 seconds before checking again
            attempt += 1
        
        if attempt >= max_attempts:
            raise TextExtractionError("Textract job timed out")
        
        # Extract text from all pages
        text_blocks = []
        confidence_scores = []
        next_token = None
        
        while True:
            if next_token:
                result = textract_client.get_document_text_detection(
                    JobId=job_id,
                    NextToken=next_token
                )
            else:
                result = textract_client.get_document_text_detection(JobId=job_id)
            
            for block in result['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block['Text'])
                    confidence_scores.append(block['Confidence'])
            
            next_token = result.get('NextToken')
            if not next_token:
                break
        
        extracted_text = '\n'.join(text_blocks)
        page_count = len(set(block.get('Page', 1) for block in result['Blocks'] if 'Page' in block))
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return extracted_text, page_count, avg_confidence
        
    except Exception as e:
        raise TextExtractionError(f"Asynchronous text extraction failed: {str(e)}")

def update_contract_status(contract_id: str, status: str) -> None:
    """Update contract status in DynamoDB"""
    try:
        table.update_item(
            Key={'contract_id': contract_id},
            UpdateExpression='SET #status = :status, updated_at = :timestamp',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': status,
                ':timestamp': generate_timestamp()
            }
        )
    except Exception as e:
        logger.warning(f"Failed to update contract status: {str(e)}")
        # Don't raise exception for status update failures