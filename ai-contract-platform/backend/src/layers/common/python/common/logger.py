import logging
import json
import os
from typing import Any, Dict, Optional

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'function': record.funcName,
            'line': record.lineno,
            'module': record.module
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'contract_id'):
            log_data['contract_id'] = record.contract_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
            
        return json.dumps(log_data)

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Set log level from environment
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        logger.setLevel(getattr(logging, log_level))
    
    return logger

def log_with_context(logger: logging.Logger, level: str, message: str, 
                    contract_id: Optional[str] = None, 
                    user_id: Optional[str] = None,
                    request_id: Optional[str] = None,
                    **kwargs) -> None:
    """Log with additional context"""
    extra = {}
    if contract_id:
        extra['contract_id'] = contract_id
    if user_id:
        extra['user_id'] = user_id
    if request_id:
        extra['request_id'] = request_id
    
    # Add any additional kwargs
    extra.update(kwargs)
    
    getattr(logger, level.lower())(message, extra=extra)