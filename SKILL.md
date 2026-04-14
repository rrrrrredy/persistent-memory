---
name: persistent-memory
description: "管理 Agent 持久化记忆系统，三层蒸馏架构（每日日志→facts.yaml→MEMORY.md）。触发词：帮我记住、记一下、别忘了、你还记得、上次说的、初始化记忆系统、设置记忆、检查记忆、记忆系统健康吗。不适用：群聊或非 owner会话（安全隔离）；一次性问题；搜索/天气/写作等无需持久化的任务。"
tags: [memory, persistent, facts, cron, daily-log]
---

# 🦞 小龙虾的记忆 (persistent-memory) V4

> 让你的 OpenClaw Agent 不再失忆。三层蒸馏架构，自动运行，无需用户操心。

---

## 路由契约

### 触发条件（满足其一即激活）
- 用户说"帮我记住 XXX"、"记一下"、"别忘了"
- 用户说"你还记得 XXX 吗"、"上次说的 XXX"
- 每日 00:00 cron 自动触发：整理昨日对话 → 写日志 → 发总结
- 每周五 18:00 cron 自动触发：蒸馏 facts.yaml + 精简 MEMORY.md
- 用户说"初始化记忆系统"、"设置记忆"、"帮我配置记忆"
- 用户说"记忆系统健康吗"、"检查记忆"

### 不触发（边界）
- ❌ 群聊或非 owner会话（安全隔离，记忆含私人信息）
- ❌ 用户只问一次性问题，不需要持久化
- ❌ 用户问"这个 skill 怎么用" → 直接说明，不执行操作
- ❌ 搜索/天气/写作等无需持久化的任务

---

## 三层记忆架构

```
每日对话
  ↓ 每日 00:00 cron 自动整理
memory/YYYY-MM-DD.md    原始日志（按日归档，超30天归档到 archive/）
  ↓ 每周五 18:00 蒸馏
memory/facts.yaml       原子事实库（联系人/规则/配置/踩坑）
  ↓ 每月精炼
MEMORY.md               核心认知（< 80 行，每次 session 必读）
```

---

## 初始化（首次安装）

**判断是否首次安装**：检查 `~/.openclaw/workspace/MEMORY.md` 是否存在。

> **`{base_dir}` 路径说明**：本 skill 文件中所有 `{base_dir}` 占位符均指本 skill 的安装目录。
> 执行前先获取实际路径：
> ```bash
> SKILL_BASE=$(find ~/.openclaw/skills -name "memory_manager.py" 2>/dev/null | head -1 | xargs dirname | xargs dirname)
> echo "base_dir = $SKILL_BASE"
> ```
> 后续所有命令中将 `{base_dir}` 替换为 `$SKILL_BASE`，例如：
> `python3 $SKILL_BASE/scripts/memory_manager.py init`

### 路径 A：首次安装

**Step 1** — 运行初始化脚本

```bash
python3 {base_dir}/scripts/memory_manager.py init
```

脚本自动创建：
- `workspace/MEMORY.md`（从模板）
- `workspace/USER.md`（从模板）
- `workspace/memory/facts.yaml`（空模板）
- `workspace/memory/` 和 `workspace/memory/archive/` 目录

**Step 2** — 引导用户填写 USER.md

主动询问并写入：
- 姓名和称呼（如"老板"、"Boss"）
- 时区（默认 Asia/Shanghai）
- 是否开启每日总结推送

**Step 3** — 设置 cron 任务

详细 cron 配置见：`references/cron-setup.md`

```bash
# 每日 00:00 整理昨日对话
openclaw cron add \
  --name "memory-daily" \
  --cron "0 0 * * *" \
  --message "执行记忆整理：读取昨日对话日志，生成结构化摘要，写入 memory 文件，发送今日总结。参考 persistent-memory skill 的每日整理流程。"

# 每周五 18:00 蒸馏（UTC 10:00 = 北京时间 18:00）
openclaw cron add \
  --name "memory-weekly" \
  --cron "0 10 * * 5" \
  --message "执行本周记忆蒸馏：读取本周所有日志，提炼新原子事实写入 facts.yaml，精简 MEMORY.md 到80行内，归档超30天日志，发送本周总结。参考 persistent-memory skill 的周五蒸馏流程。"
```

**Step 4** — 确认

```bash
python3 {base_dir}/scripts/memory_manager.py health
```

输出 `[HEALTH_STATUS] OK` 即完成。

---

### 路径 B：已有记忆系统

检查现有文件结构是否完整：

```bash
python3 {base_dir}/scripts/memory_manager.py health
```

根据 health 报告处理问题项，不覆盖已有文件。

---

## 脚本工具箱

> **原则**：确定性 I/O 操作用脚本，语义理解和摘要生成由 agent（Claude）完成。

| 命令 | 功能 |
|:---|:---|
| `init` | 初始化文件结构 |
| `digest [--date YYYY-MM-DD]` | 读取 session JSONL → 输出对话文本供 agent 摘要 |
| `write-daily [--content "..."]` | 写入今日日志（stdin 或参数） |
| `facts list` | 列出所有活跃事实 |
| `facts get <id>` | 查看指定事实 |
| `facts set` | 新增/更新事实（stdin 传 YAML） |
| `facts deactivate <id>` | 停用旧事实（不删除） |
| `health` | 检查记忆系统健康状态 |
| `archive [--days 30]` | 归档超期日志 |

```bash
# 调用格式
python3 {base_dir}/scripts/memory_manager.py <command> [args]
```

---

## 每日整理流程（00:00 cron）

```
Step 1：读取昨日对话
  python3 {base_dir}/scripts/memory_manager.py digest
  → 输出 [DIGEST_READY] 或 [DIGEST_EMPTY]

Step 2：如果 [DIGEST_EMPTY]，直接跳过，不写空文件

Step 3：agent 对输出内容生成结构化摘要：
  ✅ 完成的事
  ⏳ 待跟进（含 deadline）
  📌 重要决定/结论
  🔧 学到的规则/偏好

Step 4：写入日志
  python3 {base_dir}/scripts/memory_manager.py write-daily --content "<摘要内容>"

Step 5：判断是否有新原子事实需要加入 facts.yaml
  → 标准见下方「蒸馏判断标准」

Step 6：如已配置推送，发送今日总结给用户
```

---

## 周五蒸馏流程（18:00 cron）

```
Step 1：列出本周所有日志
  ls workspace/memory/YYYY-MM-DD.md（本周日期范围）

Step 2：读取并提炼新原子事实
  逐条对照「蒸馏判断标准」，符合条件的写入 facts.yaml：
  python3 {base_dir}/scripts/memory_manager.py facts set
  （stdin 传入 YAML 格式的事实条目）

Step 3：精简 MEMORY.md
  python3 {base_dir}/scripts/memory_manager.py health  # 先检查行数
  → 若超 80 行，执行「MEMORY.md 精简决策树」

Step 4：归档超30天日志
  python3 {base_dir}/scripts/memory_manager.py archive

Step 5：发送本周总结给用户
```

---

## 立即记忆（用户主动触发）

用户说"帮我记住 XXX"时：

1. 判断类型：
   - **事实类**（联系人/规则/配置/踩坑）→ 写入 facts.yaml
   - **事件类**（今天发生的事/任务进展）→ 写入当日日志

2. 写入：
   ```bash
   # 事实类
   python3 {base_dir}/scripts/memory_manager.py facts set
   # stdin 传入：
   # id: "fXXX"
   # content: "XXX"
   # category: "用户画像"
   # tags: ["tag1"]
   # confidence: 1.0
   # source: "用户自述"

   # 事件类
   python3 {base_dir}/scripts/memory_manager.py write-daily --append --content "📌 用户记录：XXX"
   ```

3. 回复："已记住，下次 session 还会记得。"

---

## 记忆搜索流程

用户说"你还记得 XXX 吗"时，按顺序搜索：

```
Step 1：memory_search("XXX")          ← 内置工具，语义搜索所有 memory 文件
Step 2：如有结果，memory_get(path, from, lines) 获取具体内容片段
Step 3：如无结果，检查 facts.yaml：
  python3 {base_dir}/scripts/memory_manager.py facts list
Step 4：如仍无结果，诚实回答"我没有这条记录"，不编造
```

---

## 蒸馏判断标准

以下内容**应该迁移到 facts.yaml**（原子事实，稳定不变）：

| 类型 | 示例 |
|:---|:---|
| 联系人信息 | "Zhang San, user ID: zhangsan, IM ID: 123456" |
| 固定规则/偏好 | "用户不喜欢废话开头，直接给结论" |
| 工具配置 | "Knowledge base API endpoint and credentials" |
| 踩过的坑 | "B站字幕需要 Chrome 插件 Attach Tab" |
| 定时任务 | "每日 00:00 cron ID: xxxxx" |

以下内容**留在每日日志**（事件性，有时间属性）：

- 今天完成的具体任务
- 某次对话的讨论内容
- 临时待跟进事项

以下内容**可以从 MEMORY.md 删除**（已迁移到 facts.yaml）：

- 联系人信息（facts.yaml 里已有）
- 具体工具配置参数（facts.yaml 里已有）
- 超过1个月未用到的规则

facts.yaml 格式说明见：`references/cron-setup.md`（附格式模板）

---

## MEMORY.md 精简决策树

当 MEMORY.md 超过 80 行时，按以下优先级删减：

```
1. 已有对应 facts.yaml 条目的内容 → 直接删除（facts 是权威源）
2. 超过 30 天未被引用的规则 → 删除或迁移到 facts.yaml
3. 重复或相似的条目 → 合并为一条
4. 细节性内容（步骤/配置参数）→ 迁移到 facts.yaml，MEMORY.md 只保留概要
5. 不确定删哪些 → 告知用户，附上建议删除的行范围，等确认
```

> ⚠️ 不要在未通知用户的情况下删除 MEMORY.md 内容。

---

## 记忆健康检查

```bash
python3 {base_dir}/scripts/memory_manager.py health
```

检查项：
- MEMORY.md 存在且不超80行
- USER.md 存在
- memory/ 目录存在
- facts.yaml 可读且格式正确
- 超期日志数量（>30天）

---

## 失败处理

| 场景 | 处理方式 |
|:---|:---|
| digest 无日志 | `[DIGEST_EMPTY]`，跳过，不写空文件，不报错 |
| write-daily 内容为空 | `[WRITE_DAILY_SKIP]`，跳过 |
| facts.yaml 格式损坏 | health 报告 ❌，备份原文件（`.bak`），重新初始化，告知用户 |
| 文件写入失败 | 立即告知用户，不静默失败 |
| 群聊中触发 | 拒绝执行，回复"记忆操作仅在私聊中进行" |
| MEMORY.md 超80行 | health 报告 ⚠️，提示用户蒸馏，不自动删除 |
| cron 找不到日志 | 检查 SESSION_DIR 路径是否正确（the configured `OPENCLAW_SESSION_DIR` path） |

---

## session 日志位置（OpenClaw 标准路径）

```
$OPENCLAW_SESSION_DIR/*.jsonl (default: /mnt/openclaw/.openclaw/agents/main/sessions/)
```

脚本 `digest` 命令会自动从此路径读取，无需 agent 手动 exec。

---

## 使用触发词示例

### ✅ 应该触发
```
帮我记住我叫张三，称呼老板
你还记得知识库的 API 配置吗
初始化我的记忆系统
检查一下记忆系统健康状态
```

### ❌ 不应该触发
```
帮我查一下天气          → 搜索 skill
在群里总结一下对话      → 群聊场景，拒绝
写一篇文章              → 写作 skill
```

### ⚠️ 注意区分
```
帮我记住今天开了个重要会议  → 事件类 → 写入当日日志
帮我记住张三的 IM ID 是 123 → 事实类 → 写入 facts.yaml
```

---

## 文件说明

| 文件 | 用途 | 读写频率 |
|:---|:---|:---|
| `MEMORY.md` | 核心认知，每次 session 必读 | 每周精炼 |
| `USER.md` | owner 基本信息 | 初始化后少量更新 |
| `memory/YYYY-MM-DD.md` | 每日原始日志 | 每日写入 |
| `memory/facts.yaml` | 原子事实库 | 按需更新 |
| `memory/archive/` | 超30天日志归档 | 每周五归档 |

---

## Gotchas

以下是已知的高频踩坑，执行前务必对照检查：

⚠️ `{base_dir}` 未替换为实际路径 → 执行前必须先运行 `find ~/.openclaw/skills -name "memory_manager.py"` 确认路径，脚本才能找到

⚠️ 在群聊/非 owner会话中触发 → 记忆文件含私人信息，必须检查 `chat_type == "direct"` 且 `chat_id` 匹配 owner才执行

⚠️ 用 exec+grep 搜索记忆文件 → 应使用内置 `memory_search()` 工具，支持语义匹配，速度更快且不误伤二进制文件

⚠️ facts.yaml 格式错误后直接覆盖 → 必须先备份（`.bak`）再重建，旧数据不得丢失；`active: false` 的历史条目也要保留

⚠️ MEMORY.md 超80行时自动删减 → 禁止在未告知用户的情况下删除 MEMORY.md 内容，必须列出建议删除的行范围等用户确认

⚠️ cron digest 找不到 session 日志 → 检查路径是否为 the configured `OPENCLAW_SESSION_DIR` path，容器重启后路径可能变化

⚠️ 把事件类内容写入 facts.yaml → 应区分：稳定事实（联系人/规则/配置）→ facts.yaml；有时间属性的事件 → 当日日志

⚠️ DIGEST_EMPTY 时仍写入空日志 → 收到 `[DIGEST_EMPTY]` 信号后应直接跳过，不创建空文件，否则 archive 会积累垃圾文件

---

### Hard Stop

**同一工具调用失败超过 3 次，立即停止，不再尝试。**

列出所有失败方案及原因，标记 **"需要人工介入"**，等待人工确认。

常见需要介入的场景：
- `memory_manager.py` 脚本不存在或无法执行（skill 未正确安装）
- `facts.yaml` 持续格式损坏无法写入
- session 日志路径不存在，digest 始终失败
- cron 任务创建后未生效（`openclaw cron add` 无响应）

---

## 安全约束

- ❌ 不在群聊或非 owner会话中读写记忆文件
- ❌ 不将记忆内容发送给第三方
- ❌ 不删除记忆文件（除非用户明确要求并二次确认）
- ✅ MEMORY.md 超80行时提示用户蒸馏，不擅自删除
- ✅ facts.yaml 更新时旧条目 `active: false`，不删除版本历史

---

## 更新日志

### V4.0 (2026-04-08)
- description 从多行 block scalar `|` 改为单行（符合 description 设计原则）
- 路由契约内容移入 SKILL.md 正文（新增 `## 路由契约` 章节）
- 同步 `scripts/memory_manager.py` 从安装版到 workspace 版
- 确认 `references/cron-setup.md` 存在
- 新增 `tags`（[memory, persistent, facts, cron, daily-log]）
- frontmatter: V3 → V4，H1 标题同步为 V4

### v3.0 (2026-04-08)
- B5：新增独立 `### Gotchas` 专节（8条结构化踩坑）
- B6：标准化 Hard Stop（统一格式）
- B7：H1 标题加版本号 v3
- D3：description 不触发边界加 ❌ 标记，格式更清晰
- 行数控制：cron 配置 + facts.yaml 格式模板移至 `references/cron-setup.md`
- frontmatter: V2 → V3

### v2.0 (2026-03-23)
- 新增 `scripts/memory_manager.py`（init/digest/write-daily/facts/health/archive）
- description 改为路由契约
- 补充 session 日志路径和读取方法
- 补充 cron 配置具体命令（含 prompt 模板）
- 初始化改为 agent 主动执行（自动复制模板 + 引导填写）
- 新增记忆健康检查流程
- 新增记忆搜索标准流程（memory_search 优先）
- 新增蒸馏判断标准（5条规则）
- 新增 MEMORY.md 超限精简决策树
- 新增首次安装 vs 已有记忆两条路径

### v1.0 (2026-03-20)
- 初版，三层记忆架构
