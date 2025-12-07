"""
Core interfaces for the test framework.
Defines contracts that all components must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TestStatus(Enum):
    """Test execution status"""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


@dataclass
class TestCase:
    """Standard test case structure"""

    id: str
    category: str
    input: str
    expected: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TestResult:
    """Standard test result structure"""

    test_id: str
    test_input: str
    status: TestStatus
    score: float  # 0-100
    details: Dict[str, Any]
    duration_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASS


@dataclass
class TestContext:
    """Context passed through test execution"""

    module_name: str
    mode: str
    config: Dict[str, Any]
    agent_instance: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# === Generation Interfaces ===


class IVariationStrategy(ABC):
    """Interface for test variation generation strategies"""

    @abstractmethod
    async def generate_variations(
        self, seed_input: str, count: int, context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate variations of a seed input"""
        pass


class ITestStorage(ABC):
    """Interface for storing and loading test cases"""

    @abstractmethod
    async def save(self, tests: List[TestCase], filepath: str) -> None:
        """Save test cases to storage"""
        pass

    @abstractmethod
    async def load(self, filepath: str) -> List[TestCase]:
        """Load test cases from storage"""
        pass


# === Execution Interfaces ===


class ITester(ABC):
    """Interface for individual test components"""

    @abstractmethod
    async def test(self, test_case: TestCase, context: TestContext) -> Dict[str, Any]:
        """Execute specific test logic and return results"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Tester name for reporting"""
        pass


class IExecutionMode(ABC):
    """Interface for execution modes (mock/real/hybrid)"""

    @abstractmethod
    async def execute_test(
        self, test_case: TestCase, context: TestContext, testers: List[ITester]
    ) -> TestResult:
        """Execute a single test using specified testers"""
        pass


# === Evaluation Interfaces ===


class IJudge(ABC):
    """Interface for evaluating test results"""

    @abstractmethod
    async def evaluate(
        self, test_case: TestCase, test_result: TestResult, context: TestContext
    ) -> Dict[str, Any]:
        """Evaluate test result and return assessment"""
        pass


# === Reporting Interfaces ===


class IReportFormatter(ABC):
    """Interface for formatting test reports"""

    @abstractmethod
    async def format(self, results: List[TestResult], context: TestContext) -> str:
        """Format test results into report"""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for this format (e.g., 'md', 'json')"""
        pass


class IAgentAdapter(ABC):
    """Interface for connecting to any agent implementation"""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent"""
        pass

    @abstractmethod
    async def detect_intent(self, user_input: str) -> Dict[str, Any]:
        """Detect user intent - returns modules/confidence"""
        pass

    @abstractmethod
    async def process_message(
        self, user_input: str, mode: str = "mock"
    ) -> Dict[str, Any]:
        """Process message - returns tool, params, response"""
        pass

    @abstractmethod
    def get_available_modules(self) -> List[str]:
        """Get list of available modules/capabilities"""
        pass

    @abstractmethod
    def get_available_tools(self) -> List[str]:
        """Get list of available tools"""
        pass
