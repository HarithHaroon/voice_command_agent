"""Prompt Module Manager - Loads and assembles prompt modules."""

import os
import logging
from typing import List, Dict
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptModuleManager:
    """Manages loading and assembling prompt modules dynamically."""

    def __init__(self, modules_dir: str = "prompt_modules"):
        self.modules_dir = Path(modules_dir)

        self.base_prompt = self._load_base_prompt()

        self._module_cache: Dict[str, str] = {}

        logger.info(f"PromptModuleManager initialized | Dir: {self.modules_dir}")

    def _load_base_prompt(self) -> str:
        base_path = self.modules_dir / "base.md"

        if base_path.exists():
            with open(base_path, "r", encoding="utf-8") as f:
                return f.read()

        return self._get_default_base_prompt()

    def _get_default_base_prompt(self) -> str:
        return """You are a helpful voice assistant for elderly care.
            CORE: Warm tone, brief responses (1-3 sentences), take initiative.
            TOOLS: recall_history, navigate_to_screen, start_video_call always available.
            Current date: {current_date}
        """

    def load_module(self, module_name: str) -> str:
        if module_name in self._module_cache:
            return self._module_cache[module_name]

        module_path = self.modules_dir / f"{module_name}.md"

        if module_path.exists():
            try:
                with open(module_path, "r", encoding="utf-8") as f:
                    content = f.read()

                self._module_cache[module_name] = content

                logger.info(f"Loaded module: {module_name}")

                return content
            except Exception as e:
                logger.error(f"Error loading module {module_name}: {e}")
        return ""

    def assemble_instructions(
        self,
        modules: List[str],
        user_message: str = "",
        user_name: str = "",
        current_time: str = "",
    ) -> str:
        full_instructions = self.base_prompt

        full_instructions = full_instructions.replace(
            "{current_date}", datetime.now().strftime("%A, %B %d, %Y")
        )

        full_instructions = full_instructions.replace(
            "{current_time}",
            current_time or datetime.now().strftime("%A, %B %d, %Y at %I:%M %p"),
        )

        if modules:
            full_instructions += (
                "\n\n" + "=" * 80 + "\n## ACTIVE CAPABILITIES:\n" + "=" * 80 + "\n"
            )

        for module in modules:
            content = self.load_module(module)

            if content:
                full_instructions += f"\n{content}\n"

        if user_message:
            full_instructions += (
                "\n\n"
                + "=" * 80
                + "\n## CURRENT REQUEST:\n"
                + "=" * 80
                + f"\n{user_message}\n"
            )

        logger.info(
            f"Assembled {len(modules)} modules, {len(full_instructions)} chars total"
        )
        return full_instructions

    def get_available_modules(self) -> List[str]:
        if not self.modules_dir.exists():
            return []

        return [f.stem for f in self.modules_dir.glob("*.md") if f.stem != "base"]
