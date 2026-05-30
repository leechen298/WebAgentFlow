# 开发环境搭建

## 环境要求

- Node.js `>=20`
- pnpm `>=10`
- Python `>=3.11`
- Docker Desktop 或 Docker Engine（带 Compose）

## 安装步骤

1. 复制 `.env.example` 为 `.env`。
2. 运行 `pnpm install`。
3. 创建 Python 虚拟环境：`python3.11 -m venv .venv`。
4. 运行 `.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]' -e './apps/cli'`。
   最后一个会把 `wagent` 装到 `.venv/bin/`，用于 `wagent verify`（跑场景）
   和 `wagent skill install`（给 Claude Code 安装 skill）。详见下方
   [wagent CLI 章节](#wagent-cli)。
5. 启动 API 之前先应用数据库迁移：

   ```bash
   docker compose -f infra/docker/docker-compose.yml up -d postgres
   .venv/bin/alembic -c apps/api/alembic.ini upgrade head
   ```

6. （自主探索需要）安装 Playwright Chromium：

   ```bash
   .venv/bin/python -m playwright install chromium
   ```

## 启动服务

1. 起基础设施：

   ```bash
   docker compose -f infra/docker/docker-compose.yml up -d
   ```

2. 起前端控制台：

   ```bash
   pnpm run dev:console
   ```

3. 起 API：

   ```bash
   pnpm run dev:api
   ```

   `GET /health` 应返回：

   ```json
   {
     "code": 0,
     "data": {
       "status": "ok",
       "database": "ok"
     },
     "msg": "ok"
   }
   ```

4. 起 worker：

   ```bash
   pnpm run dev:worker
   ```

5. 从独立仓库启动外部 Fixture-Site（端口 5175）：

   ```bash
   cd /Users/leechen/projects/WebAgentFlow-Fixture-Site
   pnpm dev
   ```

   配置 WebAgentFlow 使用这个外部 fixture URL 和 spec root：

   ```bash
   export WAF_FIXTURE_SITE_URL=https://example.invalid
   export WAF_PAGE_SPEC_ROOT=/path/to/WebAgentFlow-Fixture-Site/web/specs
   # 本机示例：
   export WAF_PAGE_SPEC_ROOT=/Users/leechen/projects/WebAgentFlow-Fixture-Site/web/specs
   ```

   `WAF_PAGE_SPEC_ROOT` 是 page verification 的显式 spec 来源。只有列出或
   加载 page verification specs 时需要；API 启动和 `/health` 不需要它。

也可以在主仓库根目录用 `pnpm run dev` 启动 WebAgentFlow 仓库内服务。外部
Fixture-Site 仍是本 workspace 外的独立进程。

## 构建与质量检查

- `pnpm run build`
- `pnpm run lint`
- `pnpm run format`

## wagent CLI

`wagent` 是 WebAgentFlow 的命令行工具。步骤 4 里 `pip install -e ./apps/cli`
做完后，二进制位于 `.venv/bin/wagent`。

## 项目级 Agent skills

项目专用 coding-agent skills 放在 `.agents/skills/`，并随仓库提交。这些
`SKILL.md` 是唯一事实来源。

Claude Code 从 `.claude/skills/` 发现项目级 skills，所以本仓库可以提交
`.claude/skills/<skill-name>` symlink，指向 `.agents/skills/<skill-name>`。
不要通过本地 Claude 副本反向修改 skill；先改
`.agents/skills/<skill-name>/SKILL.md`。

`.codex/` 和非 skill 的 `.claude/` 内容是本地工具配置 / 状态，继续忽略。

### 跑一次场景验证

通过 HTTP API 跑一次自主探索并打印结果 JSON。API 必须在跑（`pnpm run dev:api`）。

```bash
.venv/bin/wagent verify --url "${WAF_FIXTURE_SITE_URL:-<fixture-site-url>}/<fixture-path>" \
    --fill-values '{"<field>":"<value>"}'
```

- stdout → 一个 JSON 对象（默认裁剪过的摘要；`--full` 输出完整快照、
  `--pretty` 缩进输出）。
- stderr → 一行 banner，带 verdict + scorecard 摘要。
- exit 0 代表 `success`，1 代表其他非成功裁决，2 代表 CLI 错误。

### 安装 Claude Code skill

```bash
.venv/bin/wagent skill install     # 写入 ~/.claude/skills/verify-scenario/
.venv/bin/wagent skill uninstall   # 卸载
```

安装是幂等的 —— `git pull` 之后或者重建 venv 之后重跑一次即可刷新内嵌
的绝对路径。

之后 Claude Code 在任意项目目录都可以调用 `verify-scenario` skill（只
要 WebAgentFlow API 在跑）。汇报契约写在生成的 `SKILL.md` 里，和
[`CLAUDE.md`](../CLAUDE.md) 的执行边界章节保持一致。

---

本文为 [`dev-setup.md`](./dev-setup.md) 的中文镜像，内容以英文版为准。
