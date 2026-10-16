import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "src" / "skills"
PC_AGENT_DIR = ROOT / "src" / "agent" / "agents" / "pc_agent"


def _main_agent_skill_paths():
    tree = ast.parse((PC_AGENT_DIR / "agent.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or getattr(node.func, "id", None) != "create_deep_agent":
            continue
        for keyword in node.keywords:
            if keyword.arg == "skills":
                return ast.literal_eval(keyword.value)
    raise AssertionError("PC create_deep_agent call does not declare skills")


def _subagent_skill_paths():
    result = []
    config_dir = PC_AGENT_DIR / "subagents" / "configs"
    for path in sorted(config_dir.glob("*.yaml")):
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        result.extend(config.get("skills", []))
    return result


def _local_skill_directory(sandbox_path):
    prefix = "/skills/"
    assert sandbox_path.startswith(prefix), sandbox_path
    relative = sandbox_path[len(prefix):].strip("/")
    return SKILLS_ROOT.joinpath(*relative.split("/"))


def test_every_declared_pc_agent_skill_path_contains_skill_md():
    declared = _main_agent_skill_paths() + _subagent_skill_paths()
    pc_skill_paths = [path for path in declared if path.startswith("/skills/pc/")]

    assert pc_skill_paths, "PC Agent should declare PC-specific skills"
    missing = [
        path
        for path in declared
        if not (_local_skill_directory(path) / "SKILL.md").is_file()
    ]

    assert missing == [], f"skill declarations must point to directories containing SKILL.md: {missing}"


def test_pc_agent_uses_both_leaf_skills_and_keeps_domain_rules_as_memory():
    tree = ast.parse((PC_AGENT_DIR / "agent.py").read_text(encoding="utf-8"))
    create_call = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "create_deep_agent"
    )
    skills = ast.literal_eval(next(item.value for item in create_call.keywords if item.arg == "skills"))
    memory = ast.literal_eval(next(item.value for item in create_call.keywords if item.arg == "memory"))

    assert "/skills/pc/analysis/pc-hardware-analysis/" in skills
    assert "/skills/pc/planning/pc-build-planning/" in skills
    assert "/skills/pc/AGENTS.md" in memory
