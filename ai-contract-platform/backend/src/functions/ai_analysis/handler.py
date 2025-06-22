import json
import os
import boto3
from typing import Dict, Any, List
from common.logger import get_logger, log_with_context
from common.exceptions import AIAnalysisError, DatabaseError
from common.utils import generate_timestamp

logger = get_logger(__name__)

# Initialize AWS clients
bedrock_client = boto3.client('bedrock-runtime')
comprehend_client = boto3.client('comprehend')
dynamodb = boto3.resource('dynamodb')

# Environment variables
METADATA_TABLE = os.environ['METADATA_TABLE']
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

table = dynamodb.Table(METADATA_TABLE)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Analyze contract text using Amazon Bedrock and Comprehend"""
    request_id = context.aws_request_id
    contract_id = event.get('contract_id')
    extracted_text = event.get('extracted_text', '')
    
    try:
        log_with_context(
            logger, 'info',
            "Starting AI analysis",
            contract_id=contract_id,
            request_id=request_id
        )
        
        # Update status to processing
        update_contract_status(contract_id, 'processing_ai_analysis')
        
        # Perform contract analysis using Bedrock
        analysis_results = analyze_contract_with_bedrock(extracted_text)
        
        # Perform sentiment analysis using Comprehend
        sentiment_analysis = analyze_sentiment_with_comprehend(extracted_text)
        
        # Extract entities using Comprehend
        entity_analysis = extract_entities_with_comprehend(extracted_text)
        
        # Combine all analysis results
        comprehensive_analysis = {
            'contract_analysis': analysis_results,
            'sentiment_analysis': sentiment_analysis,
            'entity_analysis': entity_analysis
        }
        
        # Calculate risk score
        risk_score = calculate_risk_score(analysis_results, sentiment_analysis)
        
        # Store analysis results in DynamoDB
        timestamp = generate_timestamp()
        try:
            table.update_item(
                Key={'contract_id': contract_id},
                UpdateExpression='SET analysis_results = :analysis, risk_score = :risk, key_terms = :terms, missing_clauses = :missing, #status = :status, updated_at = :timestamp',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':analysis': comprehensive_analysis,
                    ':risk': risk_score,
                    ':terms': analysis_results.get('key_terms', []),
                    ':missing': analysis_results.get('missing_clauses', []),
                    ':status': 'analysis_completed',
                    ':timestamp': timestamp
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to update contract analysis: {str(e)}",
                extra={'contract_id': contract_id, 'request_id': request_id}
            )
            raise DatabaseError("Failed to update contract analysis")
        
        log_with_context(
            logger, 'info',
            f"AI analysis completed successfully. Risk score: {risk_score}",
            contract_id=contract_id,
            request_id=request_id
        )
        
        return {
            'contract_id': contract_id,
            'analysis_results': comprehensive_analysis,
            'risk_score': risk_score,
            'key_terms': analysis_results.get('key_terms', []),
            'missing_clauses': analysis_results.get('missing_clauses', []),
            'status': 'analysis_completed'
        }
        
    except Exception as e:
        logger.error(
            f"AI analysis failed: {str(e)}",
            extra={'contract_id': contract_id, 'request_id': request_id}
        )
        
        # Update status to failed
        try:
            update_contract_status(contract_id, 'ai_analysis_failed')
        except:
            pass  # Don't fail if status update fails
        
        raise e

def analyze_contract_with_bedrock(text: str) -> Dict[str, Any]:
    """Analyze contract using Amazon Bedrock Claude model"""
    try:
        prompt = f"""
        Analyze the following contract text and provide a comprehensive analysis. Focus on:
        1. Key terms and conditions
        2. Potential risks and liabilities
        3. Missing standard clauses
        4. Unusual or concerning provisions
        5. Compliance and regulatory considerations
        
        Provide your analysis in the following JSON format:
        {{
            "key_terms": ["list of key terms and conditions"],
            "risks": ["list of identified risks"],
            "missing_clauses": ["list of standard clauses that appear to be missing"],
            "unusual_provisions": ["list of unusual or concerning provisions"],
            "compliance_issues": ["list of potential compliance issues"],
            "recommendations": ["list of recommendations for improvement"],
            "summary": "Brief summary of the contract analysis"
        }}
        
        Contract text:
        {text[:8000]}  # Limit text to avoid token limits
        """
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-04",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
        
        response = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=body,
            contentType='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        # Extract the analysis from the response
        analysis_text = response_body['content'][0]['text']
        
        # Try to parse JSON from the response
        try:
            # Look for JSON content in the response
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                analysis_json = json.loads(analysis_text[json_start:json_end])
                return analysis_json
            else:
                # If no JSON found, create structured response
                return {
                    "key_terms": [],
                    "risks": [],
                    "missing_clauses": [],
                    "unusual_provisions": [],
                    "compliance_issues": [],
                    "recommendations": [],
                    "summary": analysis_text
                }
        except json.JSONDecodeError:
            # If JSON parsing fails, return raw analysis
            return {
                "key_terms": [],
                "risks": [],
                "missing_clauses": [],
                "unusual_provisions": [],
                "compliance_issues": [],
                "recommendations": [],
                "summary": analysis_text
            }
            
    except Exception as e:
        logger.error(f"Bedrock analysis failed: {str(e)}")
        raise AIAnalysisError(f"Failed to analyze contract with Bedrock: {str(e)}")

def analyze_sentiment_with_comprehend(text: str) -> Dict[str, Any]:
    """Analyze sentiment using Amazon Comprehend"""
    try:
        # Limit text length for Comprehend
        text_sample = text[:5000] if len(text) > 5000 else text
        
        response = comprehend_client.detect_sentiment(
            Text=text_sample,
            LanguageCode='en'
        )
        
        return {
            'sentiment': response['Sentiment'],
            'sentiment_scores': response['SentimentScore']
        }
        
    except Exception as e:
        logger.warning(f"Comprehend sentiment analysis failed: {str(e)}")
        return {
            'sentiment': 'NEUTRAL',
            'sentiment_scores': {
                'Positive': 0.0,
                'Negative': 0.0,
                'Neutral': 1.0,
                'Mixed': 0.0
            }
        }

def extract_entities_with_comprehend(text: str) -> Dict[str, Any]:
    """Extract entities using Amazon Comprehend"""
    try:
        # Limit text length for Comprehend
        text_sample = text[:5000] if len(text) > 5000 else text
        
        response = comprehend_client.detect_entities(
            Text=text_sample,
            LanguageCode='en'
        )
        
        # Group entities by type
        entities_by_type = {}
        for entity in response['Entities']:
            entity_type = entity['Type']
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append({
                'text': entity['Text'],
                'confidence': entity['Score']
            })
        
        return {
            'entities': entities_by_type,
            'total_entities': len(response['Entities'])
        }
        
    except Exception as e:
        logger.warning(f"Comprehend entity extraction failed: {str(e)}")
        return {
            'entities': {},
            'total_entities': 0
        }

def calculate_risk_score(analysis_results: Dict[str, Any], sentiment_analysis: Dict[str, Any]) -> float:
    """Calculate overall risk score based on analysis results"""
    try:
        risk_score = 0.0
        
        # Base risk from number of identified risks
        risks = analysis_results.get('risks', [])
        risk_score += len(risks) * 10  # 10 points per risk
        
        # Risk from missing clauses
        missing_clauses = analysis_results.get('missing_clauses', [])
        risk_score += len(missing_clauses) * 5  # 5 points per missing clause
        
        # Risk from unusual provisions
        unusual_provisions = analysis_results.get('unusual_provisions', [])
        risk_score += len(unusual_provisions) * 7  # 7 points per unusual provision
        
        # Risk from compliance issues
        compliance_issues = analysis_results.get('compliance_issues', [])
        risk_score += len(compliance_issues) * 15  # 15 points per compliance issue
        
        # Sentiment-based risk adjustment
        sentiment_scores = sentiment_analysis.get('sentiment_scores', {})
        negative_score = sentiment_scores.get('Negative', 0.0)
        risk_score += negative_score * 20  # Negative sentiment increases risk
        
        # Normalize to 0-100 scale
        risk_score = min(100.0, max(0.0, risk_score))
        
        return round(risk_score, 2)
        
    except Exception as e:
        logger.warning(f"Risk score calculation failed: {str(e)}")
        return 50.0  # Default medium risk

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