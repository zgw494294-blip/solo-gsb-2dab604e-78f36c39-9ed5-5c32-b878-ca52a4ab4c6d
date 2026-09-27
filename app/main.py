"""离线软件依赖求解 API。

POST /solve：完全离线求解，不联网查询任何包仓库。
"""

from __future__ import annotations

from fastapi import FastAPI

from .models import SolveRequest, SolveResponse
from .solver import solve as _solve

app = FastAPI(
    title="离线软件依赖求解 API",
    description="基于 catalog 与 roots 的离线版本/依赖约束求解（最多 8 个包）。",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest) -> SolveResponse:
    catalog = {
        name: [
            {"version": item.version, "dependencies": dict(item.dependencies)}
            for item in items
        ]
        for name, items in request.catalog.items()
    }
    roots = {name: rng for name, rng in request.roots.items()}

    ok, selected = _solve(catalog, roots)
    return SolveResponse(satisfiable=ok, selected=selected)
