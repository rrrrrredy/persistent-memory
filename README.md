# persistent-memory

Agent persistent memory system with 3-layer distillation: daily logs → facts.yaml → MEMORY.md.

> OpenClaw Skill — works with [OpenClaw](https://github.com/openclaw/openclaw) AI agents

## What It Does

Gives your OpenClaw agent long-term memory that survives across sessions. Uses a 3-layer distillation architecture: raw daily conversation logs are automatically summarized into structured daily notes, atomic facts are extracted into a YAML knowledge base, and key insights are periodically refined into a compact MEMORY.md (≤80 lines) loaded every session. Includes automated cron jobs for daily digestion and weekly distillation, plus on-demand "remember this" and "do you remember" workflows.

## Quick Start

```bash
openclaw skill install persistent-memory
# Or:
git clone https://github.com/rrrrrredy/persistent-memory.git ~/.openclaw/skills/persistent-memory
```

Then initialize:

```bash
python3 ~/.openclaw/skills/persistent-memory/scripts/memory_manager.py init
```

## Features

- **3-layer memory architecture**: Daily logs → facts.yaml (atomic facts) → MEMORY.md (core cognition)
- **Automated daily digestion**: 00:00 cron reads session JSONL, generates structured summaries
- **Weekly distillation**: Friday 18:00 cron extracts new facts, prunes MEMORY.md, archives old logs
- **On-demand memory**: "帮我记住 X" instantly stores facts or events in the right layer
- **Semantic search**: "你还记得 X 吗" searches across all memory layers with `memory_search()`
- **Health checks**: Validates file structure, MEMORY.md line count, facts.yaml format
- **Auto-archiving**: Logs older than 30 days are moved to `memory/archive/`
- **Safety-first**: Memory operations blocked in group chats; deletions require user confirmation

## Usage

**Trigger phrases:**
- `帮我记住`, `记一下`, `别忘了` — store information
- `你还记得`, `上次说的` — recall information
- `初始化记忆系统`, `设置记忆` — first-time setup
- `检查记忆`, `记忆系统健康吗` — health check

## Project Structure

```
persistent-memory/
├── SKILL.md                    # Main skill documentation (430 lines)
├── MEMORY.md.template          # Template for MEMORY.md initialization
├── USER.md.template            # Template for USER.md initialization
├── scripts/
│   └── memory_manager.py       # CLI tool: init, digest, write-daily, facts, health, archive
└── references/
    └── cron-setup.md           # Cron configuration guide & facts.yaml format template
```

## Requirements

- OpenClaw agent runtime
- Python 3
- Session JSONL logs at `/mnt/openclaw/.openclaw/agents/main/sessions/`

## License

[MIT](LICENSE)
