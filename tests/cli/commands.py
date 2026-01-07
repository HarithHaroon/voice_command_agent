"""
CLI commands for the multi-agent test framework.
"""

import datetime
import click
import logging
import asyncio
from pathlib import Path

from tests.core.config import ConfigManager
from tests.generation.generator import TestGenerator
from tests.generation.llm_variation_strategy import LLMVariationStrategy
from tests.storage.json_storage import JSONStorage
from tests.storage.csv_storage import CSVStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Multi-Agent Voice Assistant Test Framework CLI"""
    pass


@cli.command()
@click.option(
    "--agent",
    required=True,
    help="Agent to generate tests for (health, backlog, settings, etc.)",
)
@click.option(
    "--seed-file",
    required=True,
    help="Path to seed test cases file (CSV or JSON)",
)
@click.option(
    "--output",
    default=None,
    help="Output file path (default: tests/generated_data/{agent}_tests.json)",
)
@click.option(
    "--count",
    default=10,
    help="Number of variations per seed case",
)
@click.option(
    "--format",
    type=click.Choice(["json", "csv"]),
    default="json",
    help="Output format",
)
@click.option(
    "--regenerate",
    is_flag=True,
    help="Regenerate even if output exists",
)
@click.option(
    "--config",
    default="tests/config.yaml",
    help="Path to config file",
)
@click.option(
    "--estimate-only",
    is_flag=True,
    help="Only estimate cost, don't generate",
)
def generate(
    agent, seed_file, output, count, format, regenerate, config, estimate_only
):
    """Generate test variations from seed cases"""
    asyncio.run(
        _generate_tests(
            agent, seed_file, output, count, format, regenerate, config, estimate_only
        )
    )


async def _generate_tests(
    agent: str,
    seed_file: str,
    output: str,
    count: int,
    format: str,
    regenerate: bool,
    config_path: str,
    estimate_only: bool,
):
    """Async test generation"""
    try:
        logger.info(f"Generating test variations for agent: {agent}")

        # Load configuration
        config_manager = ConfigManager(config_path)
        gen_config = config_manager.get_generation_config()

        # Default output path
        if output is None:
            ext = "json" if format == "json" else "csv"
            output = f"tests/generated_data/{agent}_tests.{ext}"

        # Check if output exists
        output_path = Path(output)
        if output_path.exists() and not regenerate:
            click.echo(f"⚠️  Output file already exists: {output}")
            click.echo("Use --regenerate to overwrite")
            return

        # Determine storage format based on seed file extension
        seed_path = Path(seed_file)
        if seed_path.suffix == ".csv":
            storage = CSVStorage()
        else:
            storage = JSONStorage()

        # Load seed cases
        seed_cases = await storage.load(seed_file)
        logger.info(f"Loaded {len(seed_cases)} seed test cases")

        # Create generation strategy
        llm_config = gen_config.get("llm_strategy", {})
        strategy = LLMVariationStrategy(llm_config)

        # Create generator
        generator = TestGenerator(strategy, storage)

        # Estimate cost
        cost_estimate = generator.estimate_cost(len(seed_cases), count)
        click.echo(f"\n📊 Cost Estimate:")
        click.echo(f"  Seed cases: {len(seed_cases)}")
        click.echo(f"  Variations per seed: {count}")
        click.echo(f"  Total variations: {cost_estimate['total_variations']}")
        click.echo(f"  Estimated cost: ${cost_estimate['estimated_cost_usd']:.2f}")
        click.echo(f"  Model: {cost_estimate['model']}")

        if estimate_only:
            click.echo("\n✅ Estimate complete (no tests generated)")
            return

        # Check cost limit
        cost_limit = gen_config.get("cost_limits", {}).get("max_cost_per_run", 5.00)
        if cost_estimate["estimated_cost_usd"] > cost_limit:
            click.echo(
                f"\n⚠️  Warning: Estimated cost (${cost_estimate['estimated_cost_usd']:.2f}) "
                f"exceeds limit (${cost_limit:.2f})"
            )
            if not click.confirm("Continue anyway?"):
                return

        # Generate variations
        click.echo(f"\n🔄 Generating {count} variations per seed...")
        click.echo(f"Using model: {llm_config.get('model', 'gpt-4o-mini')}")

        # Choose output storage
        if format == "csv":
            output_storage = CSVStorage()
        else:
            output_storage = JSONStorage()

        generator.storage = output_storage
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


@cli.command()
@click.option(
    "--agent",
    required=True,
    help="Agent to test (health, backlog, settings, orchestrator, etc.)",
)
@click.option(
    "--mode",
    default="mock",
    type=click.Choice(["mock", "real"]),
    help="Execution mode",
)
@click.option(
    "--test-file",
    default=None,
    help="Path to test file (default: tests/generated_data/{agent}_tests.json)",
)
@click.option(
    "--config",
    default="tests/config.yaml",
    help="Path to config file",
)
@click.option(
    "--output",
    default="tests/reports",
    help="Output directory for reports",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Limit number of tests to run (for debugging)",
)
def test(agent, mode, test_file, config, output, limit):
    """Run tests for a specific agent"""
    asyncio.run(_run_tests(agent, mode, test_file, config, output, limit))


async def _run_tests(
    agent: str, mode: str, test_file: str, config_path: str, output_dir: str, limit: int
):
    """Async test execution"""
    try:
        logger.info(f"Running tests for agent: {agent} in {mode} mode")

        # Load configuration
        config_manager = ConfigManager(config_path)

        config_manager.load()

        # Default test file path
        if test_file is None:
            test_file = f"tests/generated_data/{agent}_tests.json"

        # Check if test file exists
        if not Path(test_file).exists():
            click.echo(f"❌ Test file not found: {test_file}")
            click.echo(f"💡 Generate tests first with:")
            click.echo(f"   python -m tests.cli.commands generate --agent {agent}")
            raise click.Abort()

        # Load test cases
        storage = JSONStorage()

        test_cases = await storage.load(test_file)

        # Apply limit if specified
        if limit is not None:
            test_cases = test_cases[:limit]

            logger.info(f"Limited to {limit} test cases")

        logger.info(f"Loaded {len(test_cases)} test cases from {test_file}")

        # Initialize adapter
        from tests.fixtures.multi_agent_adapter import MultiAgentAdapter

        click.echo(f"🔧 Initializing multi-agent system...")

        adapter = MultiAgentAdapter()
        await adapter.initialize(user_id="test_user_123")

        click.echo(f"✅ Agent system initialized")

        # Create test context
        from tests.core.interfaces import TestContext

        context = TestContext(
            agent_name=agent,
            mode=mode,
            config=config_manager._config,
            shared_state=adapter.shared_state,
            metadata={"mode": mode},
        )

        # Create testers
        from tests.evaluators.tool_tester import ToolTester
        from tests.evaluators.routing_tester import RoutingTester
        from tests.evaluators.handoff_tester import HandoffTester

        testers = [ToolTester(), RoutingTester(), HandoffTester()]

        # Create execution mode
        if mode == "mock":
            from tests.execution.modes.mock_mode import MockMode

            execution_mode = MockMode(adapter)
        else:  # real
            from tests.execution.modes.real_mode import RealMode

            execution_mode = RealMode(adapter)

        # Create executor
        from tests.execution.test_executor import TestExecutor

        executor = TestExecutor(execution_mode, testers)

        # Run tests
        click.echo(f"\n🧪 Executing {len(test_cases)} tests...")

        results = await executor.execute_tests(test_cases, context)

        # Generate report
        click.echo(f"\n📝 Generating report...")

        from tests.reporting.markdown_formatter import MarkdownFormatter

        formatter = MarkdownFormatter()

        report = await formatter.format(results, context)

        # Save report
        output_path = Path(output_dir)

        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        report_file = output_path / f"{agent}_{mode}_{timestamp}.md"

        with open(report_file, "w") as f:
            f.write(report)

        click.echo(f"✅ Report saved to: {report_file}")

        # Print summary
        summary = executor.generate_summary(results)
        click.echo(f"\n📊 Test Summary:")
        click.echo(f"  Total: {summary['total']}")
        click.echo(f"  Passed: {summary['passed']} ✅")
        click.echo(f"  Failed: {summary['failed']} ❌")
        click.echo(f"  Success Rate: {summary['success_rate']:.1f}%")
        click.echo(f"  Avg Duration: {summary['avg_duration_ms']:.0f}ms")

    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--scenario",
    required=True,
    help="Conversation scenario ID (e.g., health_deep_dive_001)",
)
@click.option(
    "--file",
    default="tests/seed_data/conversations/health_conversations.yaml",
    help="Path to conversation YAML file",
)
@click.option(
    "--config",
    default="tests/config.yaml",
    help="Path to config file",
)
@click.option(
    "--output",
    default="tests/reports/conversations",
    help="Output directory for reports",
)
def conversation(scenario, file, config, output):
    """Run a multi-turn conversation test"""
    asyncio.run(_run_conversation(scenario, file, config, output))


async def _run_conversation(
    scenario_id: str, yaml_file: str, config_path: str, output_dir: str
):
    """Async conversation test execution"""
    try:
        logger.info(f"Running conversation scenario: {scenario_id}")

        # Load configuration
        config_manager = ConfigManager(config_path)
        config_manager.load()

        # Load conversation
        from tests.storage.yaml_storage import YAMLStorage

        conversation = await YAMLStorage.load_conversation_by_id(yaml_file, scenario_id)
        click.echo(f"📖 Loaded conversation: {conversation.name}")
        click.echo(f"   Description: {conversation.description}")
        click.echo(f"   Turns: {len(conversation.turns)}")

        # Initialize adapter
        from tests.fixtures.multi_agent_adapter import MultiAgentAdapter

        click.echo(f"\n🔧 Initializing multi-agent system...")
        adapter = MultiAgentAdapter()
        await adapter.initialize(user_id="test_user_123")
        click.echo(f"✅ Agent system initialized")

        # Create test context
        from tests.core.interfaces import TestContext

        context = TestContext(
            agent_name="multi_turn",
            mode="real",
            config=config_manager._config,
            shared_state=adapter.shared_state,
            metadata={"mode": "real"},
        )

        # Create testers
        from tests.evaluators.tool_tester import ToolTester
        from tests.evaluators.routing_tester import RoutingTester
        from tests.evaluators.handoff_tester import HandoffTester

        testers = [ToolTester(), RoutingTester(), HandoffTester()]

        # Create conversation executor
        from tests.execution.conversation_executor import ConversationExecutor

        executor = ConversationExecutor(adapter.processor, testers)

        # Run conversation
        click.echo(f"\n💬 Executing conversation...")
        result = await executor.execute_conversation(conversation, context)

        # Generate report
        click.echo(f"\n📝 Generating report...")
        from tests.reporting.conversation_formatter import ConversationFormatter

        formatter = ConversationFormatter()
        report = await formatter.format(result, context)

        # Save report
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_file = output_path / f"{scenario_id}_{timestamp}.md"

        with open(report_file, "w") as f:
            f.write(report)

        click.echo(f"✅ Report saved to: {report_file}")

        # Print summary
        click.echo(f"\n📊 Conversation Summary:")
        click.echo(f"  Total Turns: {result.total_turns}")
        click.echo(f"  Passed: {result.passed_turns} ✅")
        click.echo(f"  Failed: {result.failed_turns} ❌")
        click.echo(f"  Success Rate: {result.overall_score:.1f}%")
        click.echo(f"  Duration: {result.duration_ms:.0f}ms")

        # Show turn-by-turn results
        click.echo(f"\n📝 Turn-by-Turn Results:")
        for i, turn_result in enumerate(result.turn_results, 1):
            status_emoji = "✅" if turn_result.passed else "❌"
            click.echo(
                f"  Turn {i}: {status_emoji} {turn_result.score:.0f}% "
                f"({turn_result.duration_ms:.0f}ms)"
            )

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error(f"Conversation test failed: {e}", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
