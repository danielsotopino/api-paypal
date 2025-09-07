from pydantic import BaseModel
from typing import Optional, List, Any, Generic, TypeVar

T = TypeVar('T')


class ApiError(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    errors: List[ApiError] = []
    
    @classmethod
    def success_response(cls, data: T) -> 'ApiResponse[T]':
        return cls(success=True, data=data, errors=[])
    
    @classmethod
    def error_response(cls, errors: List[ApiError]) -> 'ApiResponse[None]':
        return cls(success=False, data=None, errors=errors)
    
    @classmethod
    def single_error(cls, code: str, message: str) -> 'ApiResponse[None]':
        return cls.error_response([ApiError(code=code, message=message)])