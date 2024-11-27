"""
Custom exceptions for the dashboard application
"""


class DashboardError(Exception):
    """Base exception for dashboard application"""

    def __init__(self, message: str = "대시보드 오류가 발생했습니다"):
        self.message = message
        super().__init__(self.message)


class ValidationError(DashboardError):
    """Exception raised for validation errors"""

    def __init__(self, message: str = "유효성 검사 오류가 발생했습니다"):
        self.message = message
        super().__init__(self.message)


class CollectionError(DashboardError):
    """Exception raised for collection errors"""

    def __init__(self, message: str = "데이터 수집 중 오류가 발생했습니다"):
        self.message = message
        super().__init__(self.message)


class DatabaseError(DashboardError):
    """Exception raised for database errors"""

    def __init__(self, message: str = "데이터베이스 오류가 발생했습니다"):
        self.message = message
        super().__init__(self.message)


class ConfigurationError(DashboardError):
    """Exception raised for configuration errors"""

    def __init__(self, message: str = "설정 오류가 발생했습니다"):
        self.message = message
        super().__init__(self.message)


class UIError(DashboardError):
    """Exception raised for UI-related errors"""

    def __init__(self, message: str = "UI 오류가 발생했습니다"):
        self.message = message
        super().__init__(self.message)
