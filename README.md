# 离线软件依赖求解 API

使用 Python + FastAPI 实现的**离线**软件依赖求解服务：给定软件包目录（catalog）和根约束（roots），在本地通过回溯求解每个包应选择的版本。**不会联网查询任何包仓库。**

## 规则

- 最多 8 个包，每个包 1～5 个版本。
- 每个版本含正整数 `version` 与 `dependencies`（依赖包名 -> 正整数闭区间 `[min, max]`）。
- `roots` 非空，值同为闭区间 `[min, max]`。
- 仅选择从根沿**所选版本**的依赖可达的包，每个被选包恰选一个版本，满足全部根约束与传递依赖。
- 允许**可满足的循环依赖**；版本冲突时自动回溯换版。
- 存在多解时，按全部 catalog 包名排序构成版本向量（未选包记 `0`），取**字典序最大**的解。
- 无解返回 `{"satisfiable": false, "selected": {}}`。
- 非法区间（非正整数、`min > max`、长度不为 2）、同包重复版本、未知包名等非法输入返回 **422**。

## 快速开始（Docker Compose）

依赖会随构建一起安装，一条命令即可就绪：

```bash
docker compose up --build
```

服务监听宿主机 **8000** 端口。

- 健康检查：`GET http://localhost:8000/health`
- 交互式文档（Swagger UI）：`http://localhost:8000/docs`

停止：

```bash
docker compose down
```

## 请求示例

```bash
curl -s -X POST http://localhost:8000/solve \
  -H 'Content-Type: application/json' \
  -d '{
    "catalog": {
      "app": [
        {"version": 1, "dependencies": {"lib": [1, 2]}},
        {"version": 2, "dependencies": {"lib": [2, 2]}}
      ],
      "lib": [
        {"version": 1, "dependencies": {}},
        {"version": 2, "dependencies": {"common": [1, 1]}}
      ],
      "common": [
        {"version": 1, "dependencies": {}}
      ],
      "unused": [
        {"version": 1, "dependencies": {}}
      ]
    },
    "roots": {
      "app": [1, 2]
    }
  }'
```

响应（按包名排序的包名 -> 版本映射，仅包含被选包；`unused` 不可达故不选）：

```json
{
  "satisfiable": true,
  "selected": {
    "app": 2,
    "common": 1,
    "lib": 2
  }
}
```

无解示例（根要求 `app@3`，但 catalog 中不存在）：

```bash
curl -s -X POST http://localhost:8000/solve \
  -H 'Content-Type: application/json' \
  -d '{
    "catalog": {"app": [{"version": 1, "dependencies": {}}]},
    "roots": {"app": [3, 3]}
  }'
# {"satisfiable": false, "selected": {}}
```

非法输入示例（`min > max` 的非法区间）返回 HTTP 422：

```bash
curl -i -X POST http://localhost:8000/solve \
  -H 'Content-Type: application/json' \
  -d '{
    "catalog": {"app": [{"version": 1, "dependencies": {}}]},
    "roots": {"app": [3, 2]}
  }'
```

## 本地开发（不使用 Docker）

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

运行测试：

```bash
pip install pytest httpx
pytest -q
```

## 目录结构

```
app/
  solver.py    # 离线回溯求解核心（纯 Python，无框架依赖）
  models.py    # Pydantic 请求/响应模型与 422 校验
  main.py      # FastAPI 应用：POST /solve、GET /health
Dockerfile
docker-compose.yml
requirements.txt
tests/
```
