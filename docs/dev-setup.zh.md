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
4. 运行 `.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]'`。
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

5. 起 validation-site（自主探索的验证靶站）：

   ```bash
   pnpm run dev:validation
   ```

## 构建与质量检查

- `pnpm run build`
- `pnpm run lint`
- `pnpm run format`

---

本文为 [`dev-setup.md`](./dev-setup.md) 的中文镜像，内容以英文版为准。
