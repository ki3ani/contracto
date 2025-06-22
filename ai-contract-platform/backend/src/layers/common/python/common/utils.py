import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from common.exceptions import ValidationError

def generate_contract_id() -> str:
    """Generate a unique contract ID"""
    return str(uuid.uuid4())

def generate_timestamp() -> str:
    """Generate ISO format timestamp"""
    return datetime.utcnow().isoformat() + 'Z'

def validate_file_type(filename: str) -> bool:
    """Validate if file type is supported"""
    allowed_extensions = {'.pdf', '.docx', '.doc'}
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)

def create_api_response(status_code: int, body: Dict[str, Any], 
                       headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create standardized API Gateway response"""
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body)
    }

def create_error_response(error: Exception, request_id: str = None) -> Dict[str, Any]:
    """Create standardized error response"""
    if hasattr(error, 'status_code') and hasattr(error, 'error_code'):
        # Custom exception
        body = {
            'error': {
                'code': error.error_code,
                'message': error.message
            }
        }
        if request_id:
            body['request_id'] = request_id
        return create_api_response(error.status_code, body)
    else:
        # Generic exception
        body = {
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An internal error occurred'
            }
        }
        if request_id:
            body['request_id'] = request_id
        return create_api_response(500, body)

def extract_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """Extract user ID from API Gateway event"""
    try:
        return event['requestContext']['authorizer']['claims']['sub']
    except (KeyError, TypeError):
        return None

def validate_contract_metadata(metadata: Dict[str, Any]) -> None:
    """Validate contract metadata"""
    required_fields = ['filename', 'file_size', 'content_type']
    
    for field in required_fields:
        if field not in metadata:
            raise ValidationError(f"Missing required field: {field}")
    
    if not validate_file_type(metadata['filename']):
        raise ValidationError("Unsupported file type")
    
    # Validate file size (max 10MB)
    if metadata['file_size'] > 10 * 1024 * 1024:
        raise ValidationError("File size exceeds maximum limit of 10MB")