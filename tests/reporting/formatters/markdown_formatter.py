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
            self._generate_failed_tests(results, context),
            self._generate_warnings(results, context),
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

        # Group by category
        categories = {}
        for result in results:
            category = result.details.get("category", "uncategorized")
            if category not in categories:
                categories[category] = {"passed": 0, "failed": 0, "total": 0}

            categories[category]["total"] += 1
            if result.passed:
                categories[category]["passed"] += 1
            else:
                categories[category]["failed"] += 1

        avg_score = sum(r.score for r in results) / total if total > 0 else 0
        avg_duration = sum(r.duration_ms for r in results) / total if total > 0 else 0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "categories": categories,
            "avg_score": avg_score,
            "avg_duration": avg_duration,
        }

    def _generate_header(self, context: TestContext, stats: Dict) -> str:
        """Generate report header"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        return f"""# Test Report: {context.module_name}

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
        lines.append("")

        # Category breakdown
        if stats["categories"]:
            lines.append("### By Category")
            lines.append("")
            lines.append("| Category | Pass | Fail | Total | Success Rate |")
            lines.append("|----------|------|------|-------|--------------|")

            for category, data in sorted(stats["categories"].items()):
                rate = (
                    (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
                )
                lines.append(
                    f"| {category} | {data['passed']} | {data['failed']} | "
                    f"{data['total']} | {rate:.1f}% |"
                )

        return "\n".join(lines)

    def _generate_failed_tests(
        self, results: List[TestResult], context: TestContext
    ) -> str:
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

            # Tester results
            tester_results = result.details.get("tester_results", {})
            for tester_name, tester_result in tester_results.items():
                if not tester_result.get("passed", False):
                    lines.append(f"**{tester_name.title()} Test:** ❌ FAIL")

                    if "error" in tester_result:
                        lines.append(f"  - Error: {tester_result['error']}")

                    # Add specific failure details
                    if tester_name == "intent":
                        lines.append(
                            f"  - Expected modules: {tester_result.get('expected_modules', [])}"
                        )
                        lines.append(
                            f"  - Detected modules: {tester_result.get('detected_modules', [])}"
                        )
                    elif tester_name == "tool":
                        lines.append(
                            f"  - Expected tool: {tester_result.get('expected_tool')}"
                        )
                        lines.append(
                            f"  - Actual tool: {tester_result.get('actual_tool')}"
                        )

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _generate_warnings(
        self, results: List[TestResult], context: TestContext
    ) -> str:
        """Generate warnings section"""
        warnings = [r for r in results if r.status == TestStatus.WARNING]

        if not warnings:
            return None

        lines = [f"## ⚠️ Warnings ({len(warnings)})", ""]

        for result in warnings:
            lines.append(f"- **{result.test_id}:** {result.test_input}")

        return "\n".join(lines)

    def _generate_passed_tests(
        self, results: List[TestResult], context: TestContext
    ) -> str:
        """Generate passed tests section (optional, collapsible)"""
        passed = [r for r in results if r.status == TestStatus.PASS]

        if not passed or not context.config.get("include_passed_tests", False):
            return f"## ✅ Passed Tests ({len(passed)})\n\nAll passing tests executed successfully."

        lines = [
            f"## ✅ Passed Tests ({len(passed)})",
            "",
            "<details>",
            "<summary>Show all passing tests</summary>",
            "",
        ]

        for result in passed:
            lines.append(
                f"- **{result.test_id}:** {result.test_input} (score: {result.score:.1f})"
            )

        lines.append("</details>")

        return "\n".join(lines)

    def _generate_metrics(self, results: List[TestResult]) -> str:
        """Generate performance metrics section"""
        total_duration = sum(r.duration_ms for r in results)
        avg_duration = total_duration / len(results) if results else 0

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
        return "---\n\n*Generated by Voice Agent Test Framework*"
