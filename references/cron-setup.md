# persistent-memory — Cron 配置与 facts.yaml 格式参考

## Cron 任务配置

### 每日 00:00 — 整理昨日对话

```bash
openclaw cron add \
  --name "memory-daily" \
  --schedule "0 0 * * *" \
  --prompt "执行记忆整理：读取昨日对话日志，生成结构化摘要，写入 memory 文件，发送今日总结。参考 persistent-memory skill 的每日整理流程。"
```

**prompt 模板说明**：
- 触发 agent 读取 `memory_manager.py digest` 的输出
- 生成摘要格式：✅完成 / ⏳待跟进 / 📌结论 / 🔧规则偏好
- 若 `[DIGEST_EMPTY]`，跳过整个流程，不写空文件

### 每周五 18:00 — 蒸馏 + 归档

```bash
openclaw cron add \
  --name "memory-weekly" \
  --schedule "0 18 * * 5" \
  --prompt "执行本周记忆蒸馏：读取本周所有日志，提炼新原子事实写入 facts.yaml，精简 MEMORY.md 到80行内，归档超30天日志，发送本周总结。参考 persistent-memory skill 的周五蒸馏流程。"
```

### 查看已配置的 cron 任务

```bash
openclaw cron list
```

### 删除 cron 任务

```bash
openclaw cron remove --name "memory-daily"
openclaw cron remove --name "memory-weekly"
```

---

## facts.yaml 格式模板

```yaml
version: "1.0"
facts:
  - id: "f001"
    content: "用户姓名是张三，称呼为老板"   # 单条 < 80 字
    category: "用户画像"   # 用户画像/工具配置/Agent规则/经验教训/联系人/定时任务
    tags: ["姓名", "称呼"]
    confidence: 1.0
    source: "用户自述"
    created: "2026-03-20"
    updated: "2026-03-20"
    active: true

  - id: "f002"
    content: "Knowledge base API endpoint: https://api.example.com/kb, ID: 12345"
    category: "工具配置"
    tags: ["knowledge-base", "API", "config"]
    confidence: 1.0
    source: "用户配置"
    created: "2026-03-20"
    updated: "2026-03-20"
    active: true
```

### 字段说明

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `id` | string | 唯一标识，格式 `fXXX`（三位数字） |
| `content` | string | 事实内容，单条 **< 80 字**，超长需拆子条目 |
| `category` | string | 分类：用户画像 / 工具配置 / Agent规则 / 经验教训 / 联系人 / 定时任务 |
| `tags` | list | 检索标签，建议2-4个 |
| `confidence` | float | 置信度：1.0（确定）/ 0.8（很可能）/ 0.5（存疑） |
| `source` | string | 来源：用户自述 / cron推断 / Agent观察 |
| `created` | date | 首次创建日期（YYYY-MM-DD） |
| `updated` | date | 最近更新日期（YYYY-MM-DD） |
| `active` | bool | `true` = 有效；`false` = 已废弃（保留历史，不删除） |

### 更新规则

> **不删除，只标记失效**：当事实发生变化时，旧条目设置 `active: false`，新条目追加到末尾。

```yaml
# 旧条目（标记失效）
- id: "f003"
  content: "..."
  active: false   # ← 更新时设为 false

# 新条目（追加）
- id: "f003b"
  content: "（更新后的内容）"
  active: true
```
