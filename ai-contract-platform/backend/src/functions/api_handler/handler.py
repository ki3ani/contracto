import json
import os
import boto3
from typing import Dict, Any, List, Optional
from boto3.dynamodb.conditions import Key
from common.logger import get_logger, log_with_context
from common.utils import (
    create_api_response, 
    create_error_response,
    extract_user_id_from_event
)
from common.exceptions import (
    ValidationError, 
    DocumentNotFoundError, 
    AuthorizationError,
    DatabaseError
)

logger = get_logger(__name__)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
DOCUMENTS_BUCKET = os.environ['DOCUMENTS_BUCKET']
METADATA_TABLE = os.environ['METADATA_TABLE']

table = dynamodb.Table(METADATA_TABLE)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle API requests for contract operations"""
    request_id = context.aws_request_id
    
    try:
        logger.info("Processing API request", extra={'request_id': request_id})
        
        # Extract user ID from the event
        user_id = extract_user_id_from_event(event)
        if not user_id:
            raise AuthorizationError("User authentication required")
        
        # Route request based on HTTP method and path
        http_method = event['httpMethod']
        path = event['path']
        path_parameters = event.get('pathParameters', {})
        query_parameters = event.get('queryStringParameters', {}) or {}
        
        if http_method == 'GET':
            if path.endswith('/analysis'):
                # Get contract analysis
                contract_id = path_parameters.get('contract_id')
                return get_contract_analysis(contract_id, user_id, request_id)
            elif '/contracts/' in path and contract_id := path_parameters.get('contract_id'):
                # Get specific contract
                return get_contract(contract_id, user_id, request_id)
            elif path == '/contracts':
                # List contracts
                return list_contracts(user_id, query_parameters, request_id)
        
        # If no route matches, return 404
        return create_api_response(404, {'error': {'code': 'NOT_FOUND', 'message': 'Endpoint not found'}})
        
    except AuthorizationError as e:
        logger.warning(f"Authorization error: {str(e)}", extra={'request_id': request_id})
        return create_error_response(e, request_id)
    except ValidationError as e:
        logger.warning(f"Validation error: {str(e)}", extra={'request_id': request_id})
        return create_error_response(e, request_id)
    except DocumentNotFoundError as e:
        logger.info(f"Document not found: {str(e)}", extra={'request_id': request_id})
        return create_error_response(e, request_id)
    except DatabaseError as e:
        logger.error(f"Database error: {str(e)}", extra={'request_id': request_id})
        return create_error_response(e, request_id)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", extra={'request_id': request_id})
        return create_error_response(e, request_id)

def get_contract(contract_id: str, user_id: str, request_id: str) -> Dict[str, Any]:
    """Get contract metadata and details"""
    if not contract_id:
        raise ValidationError("Contract ID is required")
    
    log_with_context(
        logger, 'info',
        "Fetching contract details",
        contract_id=contract_id,
        user_id=user_id,
        request_id=request_id
    )
    
    try:
        response = table.get_item(Key={'contract_id': contract_id})
        
        if 'Item' not in response:
            raise DocumentNotFoundError(contract_id)
        
        contract = response['Item']
        
        # Verify user ownership
        if contract.get('user_id') != user_id:
            raise AuthorizationError("Access denied to this contract")
        
        # Remove sensitive fields
        contract_data = {
            'contract_id': contract['contract_id'],
            'filename': contract['filename'],
            'file_size': contract['file_size'],
            'content_type': contract['content_type'],
            'status': contract['status'],
            'created_at': contract['created_at'],
            'updated_at': contract['updated_at']
        }
        
        # Add optional fields if they exist
        if 'page_count' in contract:
            contract_data['page_count'] = contract['page_count']
        if 'extraction_confidence' in contract:
            contract_data['extraction_confidence'] = contract['extraction_confidence']
        if 'risk_score' in contract:
            contract_data['risk_score'] = contract['risk_score']
        
        return create_api_response(200, contract_data)
        
    except Exception as e:
        if isinstance(e, (DocumentNotFoundError, AuthorizationError)):
            raise e
        logger.error(
            f"Failed to fetch contract: {str(e)}",
            extra={'contract_id': contract_id, 'user_id': user_id, 'request_id': request_id}
        )
        raise DatabaseError("Failed to fetch contract details")

def get_contract_analysis(contract_id: str, user_id: str, request_id: str) -> Dict[str, Any]:
    """Get contract analysis results"""
    if not contract_id:
        raise ValidationError("Contract ID is required")
    
    log_with_context(
        logger, 'info',
        "Fetching contract analysis",
        contract_id=contract_id,
        user_id=user_id,
        request_id=request_id
    )
    
    try:
        response = table.get_item(Key={'contract_id': contract_id})
        
        if 'Item' not in response:
            raise DocumentNotFoundError(contract_id)
        
        contract = response['Item']
        
        # Verify user ownership
        if contract.get('user_id') != user_id:
            raise AuthorizationError("Access denied to this contract")
        
        # Check if analysis is available
        if 'analysis_results' not in contract:
            return create_api_response(200, {
                'contract_id': contract_id,
                'status': contract.get('status', 'unknown'),
                'message': 'Analysis not yet available'
            })
        
        analysis_data = {
            'contract_id': contract_id,
            'status': contract['status'],
            'analysis_results': contract['analysis_results'],
            'risk_score': contract.get('risk_score', 0),
            'key_terms': contract.get('key_terms', []),
            'missing_clauses': contract.get('missing_clauses', []),
            'updated_at': contract['updated_at']
        }
        
        return create_api_response(200, analysis_data)
        
    except Exception as e:
        if isinstance(e, (DocumentNotFoundError, AuthorizationError)):
            raise e
        logger.error(
            f"Failed to fetch contract analysis: {str(e)}",
            extra={'contract_id': contract_id, 'user_id': user_id, 'request_id': request_id}
        )
        raise DatabaseError("Failed to fetch contract analysis")

def list_contracts(user_id: str, query_parameters: Dict[str, str], request_id: str) -> Dict[str, Any]:
    """List user's contracts with optional filtering and pagination"""
    log_with_context(
        logger, 'info',
        "Listing user contracts",
        user_id=user_id,
        request_id=request_id
    )
    
    try:
        # Parse query parameters
        limit = min(int(query_parameters.get('limit', '10')), 100)  # Max 100 items
        status_filter = query_parameters.get('status')
        last_evaluated_key = query_parameters.get('last_key')
        
        # Build query parameters
        query_params = {
            'IndexName': 'user-id-created-at-index',
            'KeyConditionExpression': Key('user_id').eq(user_id),
            'Limit': limit,
            'ScanIndexForward': False  # Sort by created_at descending
        }
        
        # Add pagination token if provided
        if last_evaluated_key:
            try:
                query_params['ExclusiveStartKey'] = json.loads(last_evaluated_key)
            except json.JSONDecodeError:
                raise ValidationError("Invalid pagination token")
        
        # Add status filter if provided
        if status_filter:
            query_params['FilterExpression'] = Key('status').eq(status_filter)
        
        response = table.query(**query_params)
        
        # Format contract data
        contracts = []
        for item in response.get('Items', []):
            contract_data = {
                'contract_id': item['contract_id'],
                'filename': item['filename'],
                'file_size': item['file_size'],
                'content_type': item['content_type'],
                'status': item['status'],
                'created_at': item['created_at'],
                'updated_at': item['updated_at']
            }
            
            # Add optional fields
            if 'risk_score' in item:
                contract_data['risk_score'] = item['risk_score']
            if 'page_count' in item:
                contract_data['page_count'] = item['page_count']
                
            contracts.append(contract_data)
        
        result = {
            'contracts': contracts,
            'count': len(contracts)
        }
        
        # Add pagination token if there are more items
        if 'LastEvaluatedKey' in response:
            result['last_key'] = json.dumps(response['LastEvaluatedKey'])
        
        return create_api_response(200, result)
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list contracts: {str(e)}",
            extra={'user_id': user_id, 'request_id': request_id}
        )
        raise DatabaseError("Failed to list contracts")