# persistent-memory

Persistent memory system for AI agents — three-layer distillation architecture (daily logs → facts.yaml → MEMORY.md).

An [OpenClaw](https://github.com/openclaw/openclaw) Skill that gives your AI agent long-term memory across sessions.

## Installation

### Option A: OpenClaw (recommended)
```bash
# Clone to OpenClaw skills directory
git clone https://github.com/rrrrrredy/persistent-memory ~/.openclaw/skills/persistent-memory

# Run setup
python3 ~/.openclaw/skills/persistent-memory/scripts/memory_manager.py init
```

### Option B: Standalone
```bash
git clone https://github.com/rrrrrredy/persistent-memory
cd persistent-memory
python3 scripts/memory_manager.py init
```

## Dependencies

### Python packages
- `pyyaml` (`pip install pyyaml`)

### Environment Variables (optional)
- `OPENCLAW_SESSION_DIR` — path to session JSONL files (default: `/mnt/openclaw/.openclaw/agents/main/sessions`)

## Usage

### Initialize memory system
```
初始化记忆系统
```

### Store a fact
```
帮我记住张三的 ID 是 123456
```

### Recall information
```
你还记得知识库的配置吗
```

### Check health
```bash
python3 scripts/memory_manager.py health
```

### Three-Layer Architecture
```
Daily conversations
  ↓ Daily 00:00 cron
memory/YYYY-MM-DD.md    Raw daily logs (archived after 30 days)
  ↓ Weekly Friday 18:00 distillation
memory/facts.yaml       Atomic fact store (contacts/rules/config/lessons)
  ↓ Monthly refinement
MEMORY.md               Core cognition (< 80 lines, read every session)
```

### CLI Commands
| Command | Description |
|---------|-------------|
| `init` | Initialize file structure |
| `digest [--date YYYY-MM-DD]` | Extract conversation text for summarization |
| `write-daily [--content "..."]` | Write daily log |
| `facts list` | List all active facts |
| `facts get <id>` | View a specific fact |
| `facts set` | Add/update a fact (YAML via stdin) |
| `facts deactivate <id>` | Deactivate an old fact |
| `health` | Check memory system health |
| `archive [--days 30]` | Archive old logs |

## Project Structure

```
persistent-memory/
├── SKILL.md                    # Main skill definition
├── MEMORY.md.template          # Template for MEMORY.md
├── USER.md.template            # Template for USER.md
├── scripts/
│   └── memory_manager.py       # CLI tool for memory operations
├── references/
│   └── cron-setup.md           # Cron configuration & facts.yaml format
└── README.md
```

## License

MIT
