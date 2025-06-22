"""Custom exceptions for the contract platform"""

class ContractPlatformError(Exception):
    """Base exception for contract platform errors"""
    def __init__(self, message: str, error_code: str = None, status_code: int = 500):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(ContractPlatformError):
    """Raised when validation fails"""
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 400)

class DocumentNotFoundError(ContractPlatformError):
    """Raised when a document is not found"""
    def __init__(self, contract_id: str):
        super().__init__(f"Contract {contract_id} not found", "DOCUMENT_NOT_FOUND", 404)

class DocumentUploadError(ContractPlatformError):
    """Raised when document upload fails"""
    def __init__(self, message: str):
        super().__init__(message, "DOCUMENT_UPLOAD_ERROR", 400)

class TextExtractionError(ContractPlatformError):
    """Raised when text extraction fails"""
    def __init__(self, message: str):
        super().__init__(message, "TEXT_EXTRACTION_ERROR", 500)

class AIAnalysisError(ContractPlatformError):
    """Raised when AI analysis fails"""
    def __init__(self, message: str):
        super().__init__(message, "AI_ANALYSIS_ERROR", 500)

class DatabaseError(ContractPlatformError):
    """Raised when database operations fail"""
    def __init__(self, message: str):
        super().__init__(message, "DATABASE_ERROR", 500)

class AuthorizationError(ContractPlatformError):
    """Raised when authorization fails"""
    def __init__(self, message: str):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)