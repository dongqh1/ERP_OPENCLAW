"""汽车采购领域 Agent 配置。"""

from pathlib import Path

import yaml

PROMPT_FILE = Path(__file__).with_name("prompt.yaml")


def load_prompt() -> str:
    config = yaml.safe_load(PROMPT_FILE.read_text(encoding="utf-8"))
    return str(config.get("system_prompt", ""))
