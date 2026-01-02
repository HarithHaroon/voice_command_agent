"""
YAML storage for conversation tests.
Loads multi-turn conversation scenarios from YAML files.
"""

import logging
import yaml
from pathlib import Path
from typing import List

from tests.core.interfaces import ConversationTest, ConversationTurn

logger = logging.getLogger(__name__)


class YAMLStorage:
    """Load conversation tests from YAML files"""

    @staticmethod
    async def load_conversations(filepath: str) -> List[ConversationTest]:
        """
        Load conversation tests from YAML file.

        Args:
            filepath: Path to YAML file

        Returns:
            List of ConversationTest objects
        """
        path = Path(filepath)

        if not path.exists():
            logger.error(f"YAML file not found: {filepath}")
            return []

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"Empty YAML file: {filepath}")
                return []

            conversations = []

            for conv_id, conv_data in data.items():
                # Skip comments (keys starting with #)
                if conv_id.startswith("#"):
                    continue

                # Parse turns
                turns = []
                for turn_data in conv_data.get("turns", []):
                    turn = ConversationTurn(
                        input=turn_data.get("input", ""),
                        expected_agent=turn_data.get("expected_agent"),
                        expected_tool=turn_data.get("expected_tool"),
                        expected_params=turn_data.get("expected_params"),
                        context_check=turn_data.get("context_check"),
                        metadata=turn_data.get("metadata", {}),
                    )
                    turns.append(turn)

                # Create conversation test
                conversation = ConversationTest(
                    id=conv_id,
                    name=conv_data.get("name", conv_id),
                    description=conv_data.get("description", ""),
                    turns=turns,
                    metadata=conv_data.get("metadata", {}),
                )

                conversations.append(conversation)
                logger.debug(f"Loaded conversation: {conv_id} ({len(turns)} turns)")

            logger.info(f"Loaded {len(conversations)} conversations from {filepath}")
            return conversations

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {filepath}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading conversations from {filepath}: {e}")
            return []

    @staticmethod
    async def load_conversation_by_id(
        filepath: str, conversation_id: str
    ) -> ConversationTest:
        """Load a single conversation by ID"""
        conversations = await YAMLStorage.load_conversations(filepath)

        for conv in conversations:
            if conv.id == conversation_id:
                return conv

        raise ValueError(f"Conversation '{conversation_id}' not found in {filepath}")
