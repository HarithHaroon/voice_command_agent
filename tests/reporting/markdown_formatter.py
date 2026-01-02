"""
Markdown report formatter.
Generates human-readable test reports in Markdown format.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from tests.core.interfaces import IReportFormatter, TestResult, TestContext, TestStatus

logger = logging.getLogger(__name__)


class MarkdownFormatter(IReportFormatter):
    """Formats test results as Markdown"""

    @property
    def file_extension(self) -> str:
        return "md"

    async def format(self, results: List[TestResult], context: TestContext) -> str:
        """Generate Markdown report from test results"""

        if not results:
            return "# Test Report\n\nNo tests executed."

        # Calculate statistics
        stats = self._calculate_stats(results)

        # Build report sections
        sections = [
            self._generate_header(context, stats),
            self._generate_summary_table(stats),
            self._generate_failed_tests(results),
            self._generate_passed_tests(results, context),
            self._generate_metrics(results),
            self._generate_footer(),
        ]

        return "\n\n".join(filter(None, sections))

    def _calculate_stats(self, results: List[TestResult]) -> Dict[str, Any]:
        """Calculate test statistics"""
        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASS)
        failed = sum(1 for r in results if r.status == TestStatus.FAIL)
        warnings = sum(1 for r in results if r.status == TestStatus.WARNING)

        avg_score = sum(r.score for r in results) / total if total > 0 else 0
        avg_duration = sum(r.duration_ms for r in results) / total if total > 0 else 0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "avg_score": avg_score,
            "avg_duration": avg_duration,
        }

    def _generate_header(self, context: TestContext, stats: Dict) -> str:
        """Generate report header"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        return f"""# Test Report: {context.agent_name}

**Date:** {timestamp}  
**Mode:** {context.mode}  
**Total Tests:** {stats['total']}

---"""

    def _generate_summary_table(self, stats: Dict) -> str:
        """Generate summary statistics table"""
        lines = ["## 📊 Summary", ""]

        # Overall table
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| **Total Tests** | {stats['total']} |")
        lines.append(f"| **Passed** | {stats['passed']} ✅ |")
        lines.append(f"| **Failed** | {stats['failed']} ❌ |")
        lines.append(f"| **Warnings** | {stats['warnings']} ⚠️ |")
        lines.append(f"| **Success Rate** | {stats['success_rate']:.1f}% |")
        lines.append(f"| **Avg Score** | {stats['avg_score']:.1f}/100 |")

        return "\n".join(lines)

    def _generate_failed_tests(self, results: List[TestResult]) -> str:
        """Generate failed tests section"""
        failed = [r for r in results if r.status == TestStatus.FAIL]

        if not failed:
            return None

        lines = [f"## ❌ Failed Tests ({len(failed)})", ""]

        for i, result in enumerate(failed, 1):
            lines.append(f"### Test #{i}: {result.test_id}")
            lines.append(f'**Input:** "{result.test_input}"')
            lines.append(f"**Score:** {result.score:.1f}/100")
            lines.append(f"**Duration:** {result.duration_ms:.0f}ms")
            lines.append("")

            # Show tester results
            tester_results = result.details.get("tester_results", {})
            for tester_name, tester_result in tester_results.items():
                if not tester_result.get("passed", False):
                    lines.append(f"**{tester_name.title()} Test:** ❌ FAIL")

                    if "error" in tester_result:
                        lines.append(f"  - Error: {tester_result['error']}")

                    # Add specific failure details
                    if tester_name == "tool":
                        lines.append(
                            f"  - Expected tool: {tester_result.get('expected_tool')}"
                        )
                        lines.append(
                            f"  - Actual tools: {tester_result.get('actual_tools', [])}"
                        )
                    elif tester_name == "routing":
                        lines.append(
                            f"  - Expected agent: {tester_result.get('expected_agent')}"
                        )
                        lines.append(
                            f"  - Agent path: {tester_result.get('agent_path', [])}"
                        )
                    elif tester_name == "handoff":
                        lines.append(
                            f"  - Expected agent: {tester_result.get('expected_agent')}"
                        )
                        lines.append(
                            f"  - Handoffs: {tester_result.get('handoffs', [])}"
                        )

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _generate_passed_tests(
        self, results: List[TestResult], context: TestContext
    ) -> str:
        """Generate passed tests section"""
        passed = [r for r in results if r.status == TestStatus.PASS]

        if not passed:
            return None

        # Only show count, not details (to keep report concise)
        return f"## ✅ Passed Tests ({len(passed)})\n\nAll passing tests executed successfully."

    def _generate_metrics(self, results: List[TestResult]) -> str:
        """Generate performance metrics section"""
        if not results:
            return ""

        total_duration = sum(r.duration_ms for r in results)
        avg_duration = total_duration / len(results)

        lines = [
            "## 📈 Performance Metrics",
            "",
            f"- **Total Duration:** {total_duration:.0f}ms",
            f"- **Average Duration:** {avg_duration:.0f}ms per test",
            f"- **Slowest Test:** {max((r.duration_ms for r in results), default=0):.0f}ms",
            f"- **Fastest Test:** {min((r.duration_ms for r in results), default=0):.0f}ms",
        ]

        return "\n".join(lines)

    def _generate_footer(self) -> str:
        """Generate report footer"""
        return "---\n\n*Generated by Multi-Agent Voice Assistant Test Framework*"
