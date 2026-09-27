"""API 层测试：正常求解与各类 422 非法输入。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_BODY = {
    "catalog": {
        "app": [
            {"version": 1, "dependencies": {"lib": [1, 2]}},
            {"version": 2, "dependencies": {"lib": [2, 2]}},
        ],
        "lib": [
            {"version": 1, "dependencies": {}},
            {"version": 2, "dependencies": {"common": [1, 1]}},
        ],
        "common": [{"version": 1, "dependencies": {}}],
        "unused": [{"version": 1, "dependencies": {}}],
    },
    "roots": {"app": [1, 2]},
}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_solve_ok():
    resp = client.post("/solve", json=VALID_BODY)
    assert resp.status_code == 200
    assert resp.json() == {
        "satisfiable": True,
        "selected": {"app": 2, "common": 1, "lib": 2},
    }


def test_solve_unsatisfiable():
    body = {
        "catalog": {"app": [{"version": 1, "dependencies": {}}]},
        "roots": {"app": [3, 3]},
    }
    resp = client.post("/solve", json=body)
    assert resp.status_code == 200
    assert resp.json() == {"satisfiable": False, "selected": {}}


def test_solve_cycle():
    body = {
        "catalog": {
            "a": [{"version": 1, "dependencies": {"b": [1, 1]}}],
            "b": [{"version": 1, "dependencies": {"a": [1, 1]}}],
        },
        "roots": {"a": [1, 1]},
    }
    resp = client.post("/solve", json=body)
    assert resp.status_code == 200
    assert resp.json() == {"satisfiable": True, "selected": {"a": 1, "b": 1}}


@pytest.mark.parametrize(
    "body",
    [
        # 非法区间：min > max
        {"catalog": {"a": [{"version": 1}]}, "roots": {"a": [3, 2]}},
        # 非法区间：端点非正整数
        {"catalog": {"a": [{"version": 1}]}, "roots": {"a": [0, 2]}},
        # 非法区间：长度不为 2
        {"catalog": {"a": [{"version": 1}]}, "roots": {"a": [1, 2, 3]}},
        # 非法区间：依赖中的区间
        {
            "catalog": {
                "a": [{"version": 1, "dependencies": {"b": [2, 1]}}],
                "b": [{"version": 1}],
            },
            "roots": {"a": [1, 1]},
        },
        # 同包重复版本
        {
            "catalog": {"a": [{"version": 1}, {"version": 1}]},
            "roots": {"a": [1, 1]},
        },
        # 未知包名：roots
        {"catalog": {"a": [{"version": 1}]}, "roots": {"ghost": [1, 1]}},
        # 未知包名：依赖
        {
            "catalog": {"a": [{"version": 1, "dependencies": {"ghost": [1, 1]}}]},
            "roots": {"a": [1, 1]},
        },
        # roots 为空
        {"catalog": {"a": [{"version": 1}]}, "roots": {}},
        # 版本号非正整数
        {"catalog": {"a": [{"version": 0}]}, "roots": {"a": [1, 1]}},
        # 版本号为布尔
        {"catalog": {"a": [{"version": True}]}, "roots": {"a": [1, 1]}},
        # 版本号为字符串
        {"catalog": {"a": [{"version": "1"}]}, "roots": {"a": [1, 1]}},
        # 包内无版本
        {"catalog": {"a": []}, "roots": {"a": [1, 1]}},
        # 包内版本数超过 5
        {
            "catalog": {"a": [{"version": i} for i in range(1, 7)]},
            "roots": {"a": [1, 6]},
        },
        # catalog 超过 8 个包
        {
            "catalog": {f"p{i}": [{"version": 1}] for i in range(9)},
            "roots": {"p0": [1, 1]},
        },
        # catalog 为空
        {"catalog": {}, "roots": {"a": [1, 1]}},
        # 缺少 roots 字段
        {"catalog": {"a": [{"version": 1}]}},
    ],
)
def test_invalid_input_returns_422(body):
    resp = client.post("/solve", json=body)
    assert resp.status_code == 422
