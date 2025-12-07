"""
CLI commands for the test framework.
"""

import click
import logging
import asyncio
from pathlib import Path

from tests.core.config import ConfigManager
from tests.core.interfaces import TestCase, TestContext
from tests.execution.test_executor import TestExecutor
from tests.execution.testers.intent_tester import IntentTester
from tests.execution.testers.tool_tester import ToolTester
from tests.execution.modes.mock_mode import MockMode
from tests.execution.modes.real_mode import RealMode
from tests.reporting.formatters.markdown_formatter import MarkdownFormatter
from tests.generation.generator import TestGenerator
from tests.generation.strategies.llm_strategy import LLMVariationStrategy
from tests.generation.storage.json_storage import JSONStorage
from tests.adapters import create_adapter

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Voice Agent Test Framework CLI"""
    pass


@cli.command()
@click.option("--module", required=True, help="Module to test (e.g., backlog)")
@click.option(
    "--mode",
    default="mock",
    type=click.Choice(["mock", "real", "hybrid"]),
    help="Execution mode",
)
@click.option("--config", default="tests/config.yaml", help="Path to config file")
@click.option("--output", default="tests/results", help="Output directory for reports")
def test(module, mode, config, output):
    """Run tests for a specific module"""

    asyncio.run(_run_tests(module, mode, config, output))


async def _run_tests(module: str, mode: str, config_path: str, output_dir: str):
    """Async test execution"""

    try:
        logger.info(f"Running tests for module: {module} in {mode} mode")

        # Load configuration
        config_manager = ConfigManager(config_path)
        adapter_config = config_manager.get("adapter")

        # Create and initialize adapter
        logger.info("Initializing adapter...")
        adapter = create_adapter(adapter_config)
        await adapter.initialize(adapter_config)
        logger.info(f"Adapter initialized: {adapter.__class__.__name__}")

        # Load test cases from variations file
        variations_file = f"tests/variations/{module}_variations.json"

        if Path(variations_file).exists():
            storage = JSONStorage()
            test_cases = await storage.load(variations_file)
            logger.info(f"Loaded {len(test_cases)} test cases from {variations_file}")
        else:
            logger.warning(f"No variations file found: {variations_file}")
            logger.info("Creating sample test case")
            # Fallback to sample
            test_case = TestCase(
                id="sample_001",
                input="remind me to call mom at 3pm",
                category="backlog",
                expected={
                    "intent": {"modules": ["backlog"], "confidence": 0.7},
                    "tool": "add_reminder",
                    "params": {"title": "call mom", "scheduled_time": "15:00"},
                },
                metadata={"module": module},
            )

            test_cases = [test_case]

        # Create test context
        context = TestContext(
            module_name=module,
            mode=mode,
            config=config_manager._config,
            agent_instance=adapter,
            metadata={"mode": mode},
        )

        logger.info(f"Context agent_instance: {context.agent_instance}")
        logger.info(f"Adapter type: {type(adapter)}")

        # Create testers
        intent_tester = IntentTester()
        tool_tester = ToolTester()
        testers = [intent_tester, tool_tester]

        execution_mode = None

        # Create execution mode
        if mode == "mock":
            execution_mode = MockMode(adapter)

        elif mode == "real":
            execution_mode = RealMode(adapter)

        elif mode == "hybrid":
            # TODO: Implement hybrid mode
            raise NotImplementedError(f"Hybrid mode not yet implemented")
        else:
            raise ValueError(f"Unknown mode: {mode}")
        # Create executor
        executor = TestExecutor(execution_mode, testers)

        # Run tests
        logger.info("Executing tests...")
        results = await executor.execute_tests(test_cases, context)

        # Generate report
        logger.info("Generating report...")
        formatter = MarkdownFormatter()
        report = await formatter.format(results, context)

        # Save report
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        report_file = output_path / f"{module}_{mode}_report.md"

        with open(report_file, "w") as f:
            f.write(report)

        logger.info(f"Report saved to: {report_file}")

        # Print summary
        summary = executor.generate_summary(results)
        click.echo("\n📊 Test Summary:")
        click.echo(f"  Total: {summary['total']}")
        click.echo(f"  Passed: {summary['passed']} ✅")
        click.echo(f"  Failed: {summary['failed']} ❌")
        click.echo(f"  Warnings: {summary['warnings']} ⚠️")
        click.echo(f"\n📄 Full report: {report_file}")

    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--module", required=True, help="Module to generate tests for")
@click.option("--seed-file", required=True, help="Path to seed test cases JSON file")
@click.option(
    "--output",
    default=None,
    help="Output file path (default: tests/variations/{module}_variations.json)",
)
@click.option("--count", default=5, help="Number of variations per seed case")
@click.option("--regenerate", is_flag=True, help="Regenerate even if output exists")
@click.option("--config", default="tests/config.yaml", help="Path to config file")
def generate(module, seed_file, output, count, regenerate, config):
    """Generate test variations from seed cases"""

    asyncio.run(_generate_tests(module, seed_file, output, count, regenerate, config))


async def _generate_tests(
    module: str,
    seed_file: str,
    output: str,
    count: int,
    regenerate: bool,
    config_path: str,
):
    """Async test generation"""

    try:
        logger.info(f"Generating test variations for module: {module}")

        # Load configuration
        config_manager = ConfigManager(config_path)
        gen_config = config_manager.get("generation")

        # Default output path
        if output is None:
            output = f"tests/variations/{module}_variations.json"

        # Check if output exists
        output_path = Path(output)
        if output_path.exists() and not regenerate:
            click.echo(f"⚠️  Output file already exists: {output}")
            click.echo("Use --regenerate to overwrite")
            return

        # Load seed cases
        storage = JSONStorage()
        seed_cases = await storage.load(seed_file)
        logger.info(f"Loaded {len(seed_cases)} seed test cases")

        # Create generation strategy
        llm_config = gen_config.get("llm_strategy", {})
        strategy = LLMVariationStrategy(llm_config)

        # Create generator
        generator = TestGenerator(strategy, storage)

        # Generate variations
        click.echo(f"Generating {count} variations per seed...")
        click.echo(f"Using model: {llm_config.get('model', 'gpt-4o-mini')}")

        all_cases = await generator.generate_from_seeds(
            seed_cases=seed_cases,
            variations_per_seed=count,
        )

        # Save results
        await generator.save_tests(all_cases, output)

        # Print summary
        click.echo(f"\n📊 Generation Summary:")
        click.echo(f"  Seed cases: {len(seed_cases)}")
        click.echo(f"  Variations generated: {len(all_cases) - len(seed_cases)}")
        click.echo(f"  Total test cases: {len(all_cases)}")
        click.echo(f"\n✅ Test variations generated successfully!")
        click.echo(f"Output: {output}")

    except Exception as e:
        logger.error(f"Test generation failed: {e}", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
