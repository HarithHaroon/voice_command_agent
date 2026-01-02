"""
Core interfaces for the multi-agent test framework.
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
    """Standard test case structure for multi-agent system"""

    id: str
    agent: str  # Which agent should handle this (orchestrator, health, backlog, etc.)
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
class AgentTrajectory:
    """Represents the path an agent takes through the system"""

    agents_visited: List[str]  # ["Orchestrator", "HealthAgent", "Orchestrator"]
    tools_called: List[str]  # ["get_health_summary"]
    handoffs: List[Dict[str, str]]  # [{"from": "Orchestrator", "to": "HealthAgent"}]
    duration_ms: float


@dataclass
class TestContext:
    """Context passed through test execution"""

    agent_name: str
    mode: str  # "mock" or "real"
    config: Dict[str, Any]
    shared_state: Any = None  # Reference to agent's SharedState
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


# ============================================================================
# Multi-Turn Conversation Testing
# ============================================================================


@dataclass
class ConversationTurn:
    """Single turn in a multi-turn conversation"""

    input: str
    expected_agent: Optional[str] = None
    expected_tool: Optional[str] = None
    expected_params: Optional[Dict[str, Any]] = None
    context_check: Optional[str] = None  # Human-readable expectation
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationTest:
    """Multi-turn conversation test"""

    id: str
    name: str
    description: str
    turns: List[ConversationTurn]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationResult:
    """Result of a conversation test"""

    test_id: str
    test_name: str
    status: TestStatus
    total_turns: int
    passed_turns: int
    failed_turns: int
    turn_results: List[TestResult]
    overall_score: float
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASS
