#!/usr/bin/env python3
"""
memory_manager.py - persistent-memory 记忆系统管理脚本 v2.0

职责：处理所有确定性 I/O 操作，语义理解和摘要生成交给 agent（Claude）

子命令：
  init          初始化记忆文件结构（首次安装）
  digest        读取 session JSONL → 提取对话文本，供 agent 生成摘要
  write-daily   写入今日日志（接收 stdin 内容）
  facts         管理 facts.yaml（get / set / list / deactivate）
  health        检查记忆系统健康状态
  archive       归档超 N 天的日志文件

用法：
  python3 memory_manager.py <subcommand> [args...]
"""

import sys
import os
import json
import shutil
import glob
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# ─── 路径常量 ─────────────────────────────────────────────────────────────────

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
ARCHIVE_DIR = os.path.join(MEMORY_DIR, "archive")
MEMORY_MD = os.path.join(WORKSPACE, "MEMORY.md")
USER_MD = os.path.join(WORKSPACE, "USER.md")
FACTS_YAML = os.path.join(MEMORY_DIR, "facts.yaml")

# session JSONL 路径（OpenClaw 标准路径）
# Session JSONL path — adjust for your OpenClaw installation
SESSION_DIR = os.environ.get("OPENCLAW_SESSION_DIR", "/mnt/openclaw/.openclaw/agents/main/sessions")

# 脚本自身所在目录（用于找模板）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

MEMORY_LINE_LIMIT = 80

# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def daily_log_path(date_str: str = None) -> str:
    d = date_str or today_str()
    return os.path.join(MEMORY_DIR, f"{d}.md")

def yesterday_str() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

def read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None

def write_file(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def append_file(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)

def count_lines(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

# ─── init ─────────────────────────────────────────────────────────────────────

def cmd_init(args):
    """
    初始化记忆文件结构。
    - 如果 MEMORY.md 已存在，跳过（不覆盖）
    - 创建目录结构
    - 复制模板文件
    - 输出初始化摘要给 agent
    """
    results = []

    # 创建目录
    for d in [MEMORY_DIR, ARCHIVE_DIR]:
        os.makedirs(d, exist_ok=True)
        results.append(f"✅ 目录: {d}")

    # MEMORY.md
    if not os.path.exists(MEMORY_MD):
        template = os.path.join(SKILL_DIR, "MEMORY.md.template")
        if os.path.exists(template):
            shutil.copy(template, MEMORY_MD)
            results.append(f"✅ 创建: {MEMORY_MD}（从模板）")
        else:
            default_content = "# MEMORY.md - 长期记忆\n> 目标：< 80 行。\n\n## 我是谁\n- **名字**：\n- **主人**：\n\n## 核心规则\n\n"
            write_file(MEMORY_MD, default_content)
            results.append(f"✅ 创建: {MEMORY_MD}（默认内容）")
    else:
        results.append(f"⏭️  跳过: {MEMORY_MD}（已存在）")

    # USER.md
    if not os.path.exists(USER_MD):
        template = os.path.join(SKILL_DIR, "USER.md.template")
        if os.path.exists(template):
            shutil.copy(template, USER_MD)
            results.append(f"✅ 创建: {USER_MD}（从模板，请填写基本信息）")
        else:
            results.append(f"⚠️  未找到 USER.md.template，请手动创建 {USER_MD}")
    else:
        results.append(f"⏭️  跳过: {USER_MD}（已存在）")

    # facts.yaml
    if not os.path.exists(FACTS_YAML):
        template = os.path.join(SKILL_DIR, "memory", "facts.yaml.template")
        if os.path.exists(template):
            shutil.copy(template, FACTS_YAML)
            results.append(f"✅ 创建: {FACTS_YAML}（从模板）")
        else:
            write_file(FACTS_YAML, 'version: "1.0"\nfacts: []\n')
            results.append(f"✅ 创建: {FACTS_YAML}（空模板）")
    else:
        results.append(f"⏭️  跳过: {FACTS_YAML}（已存在）")

    print("\n".join(results))
    print(f"\n[INIT_DONE] workspace={WORKSPACE}")
    print("下一步：请告诉 agent 引导用户填写 USER.md（姓名/称呼/时区）")

# ─── digest ───────────────────────────────────────────────────────────────────

def cmd_digest(args):
    """
    读取指定日期（默认昨日）的 session JSONL，提取对话文本。
    输出给 agent，由 agent 生成结构化摘要后调用 write-daily 写入。

    输出格式：
    [DIGEST_READY]
    date: YYYY-MM-DD
    turns: N
    ---
    (对话内容)
    """
    date_str = args.date or yesterday_str()

    # 找该日期的所有 session 文件
    pattern = os.path.join(SESSION_DIR, f"{date_str}*.jsonl")
    files = sorted(glob.glob(pattern))

    # 也尝试找文件内有该日期消息的文件（文件名可能是创建时间）
    if not files:
        all_files = sorted(glob.glob(os.path.join(SESSION_DIR, "*.jsonl")))
        files = [f for f in all_files if _jsonl_has_date(f, date_str)]

    if not files:
        print(f"[DIGEST_EMPTY] date={date_str} 未找到 session 文件，跳过。")
        return

    turns = []
    for fpath in files:
        turns.extend(_parse_jsonl(fpath, date_str))

    if not turns:
        print(f"[DIGEST_EMPTY] date={date_str} 文件存在但无对话内容，跳过。")
        return

    print(f"[DIGEST_READY]")
    print(f"date: {date_str}")
    print(f"turns: {len(turns)}")
    print(f"---")
    for t in turns:
        role = t.get("role", "unknown")
        content = t.get("content", "")
        if isinstance(content, list):
            # 处理多段内容
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
            )
        if content and content.strip():
            print(f"[{role}] {content[:500]}")
            print()

def _jsonl_has_date(fpath: str, date_str: str) -> bool:
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                if date_str in line:
                    return True
    except Exception:
        pass
    return False

def _parse_jsonl(fpath: str, date_str: str = None) -> List[Dict]:
    turns = []
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    # 过滤日期（如果指定）
                    ts = obj.get("timestamp", obj.get("created_at", ""))
                    if date_str and date_str not in ts:
                        continue
                    # 只取用户和 assistant 消息
                    if obj.get("role") in ("user", "assistant"):
                        turns.append(obj)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return turns

# ─── write-daily ──────────────────────────────────────────────────────────────

def cmd_write_daily(args):
    """
    写入今日（或指定日期）日志。
    内容从 stdin 读取，或通过 --content 参数传入。

    用法：
      echo "今日摘要内容" | python3 memory_manager.py write-daily
      python3 memory_manager.py write-daily --date 2026-03-23 --content "内容"
      python3 memory_manager.py write-daily --append  # 追加而非覆盖
    """
    date_str = args.date or today_str()
    log_path = daily_log_path(date_str)

    # 读取内容
    if args.content:
        content = args.content
    else:
        content = sys.stdin.read().strip()

    if not content:
        print(f"[WRITE_DAILY_SKIP] 内容为空，跳过写入。")
        return

    # 加时间戳头
    timestamp = datetime.now().strftime("%H:%M")
    header = f"\n## {timestamp} 每日记录\n\n"
    full_content = header + content + "\n"

    if args.append and os.path.exists(log_path):
        append_file(log_path, full_content)
        print(f"[WRITE_DAILY_OK] 追加写入: {log_path}")
    else:
        # 如果文件已存在，追加到末尾（一天可能有多次记录）
        if os.path.exists(log_path):
            append_file(log_path, full_content)
            print(f"[WRITE_DAILY_OK] 追加写入（文件已存在）: {log_path}")
        else:
            day_header = f"# 日志 {date_str}\n"
            write_file(log_path, day_header + full_content)
            print(f"[WRITE_DAILY_OK] 新建写入: {log_path}")

# ─── facts ────────────────────────────────────────────────────────────────────

def cmd_facts(args):
    """
    管理 facts.yaml
    子命令：list / get <id> / set <yaml片段> / deactivate <id>
    """
    import yaml

    def load_facts():
        if not os.path.exists(FACTS_YAML):
            return {"version": "1.0", "facts": []}
        try:
            with open(FACTS_YAML, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {"version": "1.0", "facts": []}
        except Exception as e:
            print(f"[FACTS_ERROR] 读取失败: {e}")
            sys.exit(1)

    def save_facts(data):
        with open(FACTS_YAML, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    action = args.facts_action

    if action == "list":
        data = load_facts()
        facts = data.get("facts", [])
        active = [f for f in facts if f.get("active", True)]
        print(f"[FACTS_LIST] 共 {len(active)} 条活跃事实（总 {len(facts)} 条）")
        for f in active:
            print(f"  {f.get('id', '?')} [{f.get('category', '?')}] {f.get('content', '')[:80]}")

    elif action == "get":
        if not args.fact_id:
            print("[FACTS_ERROR] 请提供 fact id")
            sys.exit(1)
        data = load_facts()
        for f in data.get("facts", []):
            if f.get("id") == args.fact_id:
                print(json.dumps(f, ensure_ascii=False, indent=2))
                return
        print(f"[FACTS_NOT_FOUND] id={args.fact_id}")

    elif action == "set":
        # 从 stdin 读取 YAML 片段
        import yaml as _yaml
        raw = args.content or sys.stdin.read().strip()
        try:
            new_fact = _yaml.safe_load(raw)
        except Exception as e:
            print(f"[FACTS_ERROR] YAML 解析失败: {e}")
            sys.exit(1)

        data = load_facts()
        facts = data.get("facts", [])

        # 检查 id 是否已存在
        existing_ids = {f.get("id") for f in facts}
        fid = new_fact.get("id")
        if fid in existing_ids:
            # 将旧条目标记为 inactive
            for f in facts:
                if f.get("id") == fid:
                    f["active"] = False
                    f["updated"] = today_str()
            # 追加新条目（新 id 加 _v2 后缀）
            new_fact["id"] = fid + "_v2"
            new_fact["active"] = True
            new_fact["created"] = today_str()
            new_fact["updated"] = today_str()
            facts.append(new_fact)
            print(f"[FACTS_UPDATED] 旧条目 {fid} 已 deactivate，新条目 id={new_fact['id']}")
        else:
            new_fact.setdefault("active", True)
            new_fact.setdefault("created", today_str())
            new_fact.setdefault("updated", today_str())
            facts.append(new_fact)
            print(f"[FACTS_SET_OK] id={fid}")

        data["facts"] = facts
        save_facts(data)

    elif action == "deactivate":
        if not args.fact_id:
            print("[FACTS_ERROR] 请提供 fact id")
            sys.exit(1)
        data = load_facts()
        found = False
        for f in data.get("facts", []):
            if f.get("id") == args.fact_id:
                f["active"] = False
                f["updated"] = today_str()
                found = True
        if found:
            save_facts(data)
            print(f"[FACTS_DEACTIVATED] id={args.fact_id}")
        else:
            print(f"[FACTS_NOT_FOUND] id={args.fact_id}")

    else:
        print(f"[FACTS_ERROR] 未知子命令: {action}，可用: list / get / set / deactivate")

# ─── health ───────────────────────────────────────────────────────────────────

def cmd_health(args):
    """
    检查记忆系统健康状态，输出结构化报告
    """
    issues = []
    ok = []

    # 1. MEMORY.md 存在且不超限
    if os.path.exists(MEMORY_MD):
        lines = count_lines(MEMORY_MD)
        if lines > MEMORY_LINE_LIMIT:
            issues.append(f"⚠️  MEMORY.md 超限: {lines} 行（限制 {MEMORY_LINE_LIMIT} 行），需蒸馏精简")
        else:
            ok.append(f"✅ MEMORY.md: {lines}/{MEMORY_LINE_LIMIT} 行")
    else:
        issues.append(f"❌ MEMORY.md 不存在: {MEMORY_MD}（请运行 init）")

    # 2. USER.md 存在
    if os.path.exists(USER_MD):
        ok.append(f"✅ USER.md 存在")
    else:
        issues.append(f"⚠️  USER.md 不存在: {USER_MD}（建议创建）")

    # 3. memory/ 目录存在
    if os.path.isdir(MEMORY_DIR):
        ok.append(f"✅ memory/ 目录存在")
    else:
        issues.append(f"❌ memory/ 目录不存在: {MEMORY_DIR}（请运行 init）")

    # 4. facts.yaml 存在且可读
    if os.path.exists(FACTS_YAML):
        try:
            import yaml
            with open(FACTS_YAML, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            active_count = sum(1 for x in data.get("facts", []) if x.get("active", True))
            ok.append(f"✅ facts.yaml: {active_count} 条活跃事实")
        except Exception as e:
            issues.append(f"❌ facts.yaml 解析失败: {e}（文件可能损坏）")
    else:
        issues.append(f"⚠️  facts.yaml 不存在: {FACTS_YAML}（运行 init 创建）")

    # 5. 今日日志
    today_log = daily_log_path()
    if os.path.exists(today_log):
        ok.append(f"✅ 今日日志存在: {today_log}")
    else:
        ok.append(f"ℹ️  今日日志待创建: {today_log}")

    # 6. 昨日日志
    yesterday_log = daily_log_path(yesterday_str())
    if os.path.exists(yesterday_log):
        ok.append(f"✅ 昨日日志存在: {yesterday_log}")
    else:
        ok.append(f"ℹ️  昨日日志不存在（可能昨日无对话）")

    # 7. 超期日志数量
    cutoff = datetime.now() - timedelta(days=30)
    old_logs = []
    for f in glob.glob(os.path.join(MEMORY_DIR, "????-??-??.md")):
        basename = os.path.basename(f).replace(".md", "")
        try:
            file_date = datetime.strptime(basename, "%Y-%m-%d")
            if file_date < cutoff:
                old_logs.append(f)
        except Exception:
            pass
    if old_logs:
        issues.append(f"⚠️  {len(old_logs)} 个日志超过30天，建议归档（运行 archive）")
    else:
        ok.append(f"✅ 无超期日志")

    # 输出报告
    print("[HEALTH_REPORT]")
    for msg in ok:
        print(f"  {msg}")
    for msg in issues:
        print(f"  {msg}")

    if issues:
        print(f"\n[HEALTH_STATUS] WARNING: {len(issues)} 个问题需处理")
    else:
        print(f"\n[HEALTH_STATUS] OK")

# ─── archive ──────────────────────────────────────────────────────────────────

def cmd_archive(args):
    """
    归档超 N 天（默认30天）的日志文件到 memory/archive/
    """
    days = args.days or 30
    cutoff = datetime.now() - timedelta(days=days)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    archived = []
    for f in glob.glob(os.path.join(MEMORY_DIR, "????-??-??.md")):
        basename = os.path.basename(f).replace(".md", "")
        try:
            file_date = datetime.strptime(basename, "%Y-%m-%d")
            if file_date < cutoff:
                dest = os.path.join(ARCHIVE_DIR, os.path.basename(f))
                shutil.move(f, dest)
                archived.append(os.path.basename(f))
        except Exception:
            pass

    if archived:
        print(f"[ARCHIVE_OK] 归档 {len(archived)} 个文件到 {ARCHIVE_DIR}:")
        for name in archived:
            print(f"  {name}")
    else:
        print(f"[ARCHIVE_SKIP] 无需归档（无超过 {days} 天的日志）")

# ─── CLI 入口 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="persistent-memory 记忆系统管理工具 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令示例：
  python3 memory_manager.py init
  python3 memory_manager.py digest --date 2026-03-22
  python3 memory_manager.py write-daily --content "今日摘要..."
  echo "内容" | python3 memory_manager.py write-daily --append
  python3 memory_manager.py facts list
  python3 memory_manager.py facts get f001
  python3 memory_manager.py facts deactivate f001
  python3 memory_manager.py health
  python3 memory_manager.py archive --days 30
"""
    )
    subparsers = parser.add_subparsers(dest="command")

    # init
    subparsers.add_parser("init", help="初始化记忆文件结构")

    # digest
    p_digest = subparsers.add_parser("digest", help="读取 session JSONL，输出对话文本供 agent 生成摘要")
    p_digest.add_argument("--date", help="日期 YYYY-MM-DD（默认昨日）")

    # write-daily
    p_write = subparsers.add_parser("write-daily", help="写入日志（从 stdin 或 --content）")
    p_write.add_argument("--date", help="日期 YYYY-MM-DD（默认今日）")
    p_write.add_argument("--content", help="日志内容（不传则从 stdin 读）")
    p_write.add_argument("--append", action="store_true", help="追加到已有文件末尾")

    # facts
    p_facts = subparsers.add_parser("facts", help="管理 facts.yaml")
    p_facts.add_argument("facts_action", choices=["list", "get", "set", "deactivate"], help="操作")
    p_facts.add_argument("fact_id", nargs="?", help="fact id（get/deactivate 用）")
    p_facts.add_argument("--content", help="YAML 内容（set 用，不传则从 stdin 读）")

    # health
    subparsers.add_parser("health", help="检查记忆系统健康状态")

    # archive
    p_archive = subparsers.add_parser("archive", help="归档超期日志")
    p_archive.add_argument("--days", type=int, default=30, help="超过多少天归档（默认30）")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "digest":
        cmd_digest(args)
    elif args.command == "write-daily":
        cmd_write_daily(args)
    elif args.command == "facts":
        cmd_facts(args)
    elif args.command == "health":
        cmd_health(args)
    elif args.command == "archive":
        cmd_archive(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
