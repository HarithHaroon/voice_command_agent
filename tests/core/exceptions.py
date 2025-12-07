"""
Custom exceptions for the test framework.
"""


class TestFrameworkError(Exception):
    """Base exception for all test framework errors"""

    pass


class ConfigurationError(TestFrameworkError):
    """Raised when configuration is invalid or missing"""

    pass


class TestGenerationError(TestFrameworkError):
    """Raised when test generation fails"""

    pass


class TestExecutionError(TestFrameworkError):
    """Raised when test execution fails"""

    pass


class AdapterError(TestFrameworkError):
    """Raised when agent adapter encounters an error"""

    pass


class StorageError(TestFrameworkError):
    """Raised when storage operations fail"""

    pass


class EvaluationError(TestFrameworkError):
    """Raised when evaluation/judging fails"""

    pass


class ReportGenerationError(TestFrameworkError):
    """Raised when report generation fails"""

    pass


class InvalidTestCaseError(TestFrameworkError):
    """Raised when test case structure is invalid"""

    def __init__(self, test_id: str, reason: str):
        self.test_id = test_id
        self.reason = reason
        super().__init__(f"Invalid test case '{test_id}': {reason}")


class AgentNotInitializedError(AdapterError):
    """Raised when agent is not properly initialized"""

    pass


class UnsupportedModeError(TestExecutionError):
    """Raised when execution mode is not supported"""

    def __init__(self, mode: str, supported_modes: list):
        self.mode = mode
        self.supported_modes = supported_modes
        super().__init__(
            f"Mode '{mode}' not supported. Available modes: {', '.join(supported_modes)}"
        )
