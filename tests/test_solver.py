"""求解核心单元测试 + 与暴力枚举参考实现的对拍测试。"""

from __future__ import annotations

import itertools
import random

from app.solver import solve


def make_catalog(spec):
    """spec: {name: [(version, {dep: (lo, hi)}), ...]}"""
    return {
        name: [
            {"version": v, "dependencies": {d: list(r) for d, r in deps.items()}}
            for v, deps in versions
        ]
        for name, versions in spec.items()
    }


def brute_force(catalog, roots):
    """参考实现：枚举全部版本组合，验证语义后取向量最大者。"""
    names = sorted(catalog)
    versions = {n: [it["version"] for it in catalog[n]] for n in names}
    deps = {
        (n, it["version"]): {d: tuple(r) for d, r in it["dependencies"].items()}
        for n in names
        for it in catalog[n]
    }
    best = None
    for combo in itertools.product(*(versions[n] for n in names)):
        assign = dict(zip(names, combo))
        if any(not (lo <= assign[r] <= hi) for r, (lo, hi) in roots.items()):
            continue
        # 从根沿所选版本的依赖计算可达集
        reachable = set(roots)
        stack = list(roots)
        while stack:
            p = stack.pop()
            for d in deps[p, assign[p]]:
                if d not in reachable:
                    reachable.add(d)
                    stack.append(d)
        # 闭包：所有依赖目标都必须可达（即被选择）
        if any(d not in reachable for p in reachable for d in deps[p, assign[p]]):
            continue
        # 约束满足：可达包的所有依赖区间都被满足
        if any(
            not (lo <= assign[d] <= hi)
            for p in reachable
            for d, (lo, hi) in deps[p, assign[p]].items()
        ):
            continue
        vec = tuple(assign[n] if n in reachable else 0 for n in names)
        if best is None or vec > best:
            best = vec
    if best is None:
        return False, {}
    return True, {n: v for n, v in zip(names, best) if v != 0}


class TestSolver:
    def test_simple_chain(self):
        catalog = make_catalog(
            {
                "app": [(1, {"lib": (1, 2)}), (2, {"lib": (2, 2)})],
                "lib": [(1, {}), (2, {})],
            }
        )
        ok, sel = solve(catalog, {"app": (1, 2)})
        assert ok
        # 字典序最大：app=2 -> lib=2
        assert sel == {"app": 2, "lib": 2}

    def test_unreachable_not_selected(self):
        catalog = make_catalog(
            {
                "app": [(1, {})],
                "extra": [(5, {})],
            }
        )
        ok, sel = solve(catalog, {"app": (1, 1)})
        assert ok
        assert sel == {"app": 1}

    def test_cycle_satisfiable(self):
        catalog = make_catalog(
            {
                "a": [(1, {"b": (1, 1)})],
                "b": [(1, {"a": (1, 1)})],
            }
        )
        ok, sel = solve(catalog, {"a": (1, 1)})
        assert ok
        assert sel == {"a": 1, "b": 1}

    def test_cycle_requires_backtracking(self):
        # a@2 与 b@1 的循环约束冲突，必须回溯到 a@1
        catalog = make_catalog(
            {
                "a": [(1, {"b": (1, 1)}), (2, {"b": (2, 2)})],
                "b": [(1, {"a": (1, 1)}), (2, {"a": (9, 9)})],
            }
        )
        ok, sel = solve(catalog, {"a": (1, 2)})
        assert ok
        assert sel == {"a": 1, "b": 1}

    def test_unsatisfiable_root_range(self):
        catalog = make_catalog({"app": [(1, {}), (2, {})]})
        ok, sel = solve(catalog, {"app": (3, 5)})
        assert not ok
        assert sel == {}

    def test_unsatisfiable_dependency(self):
        catalog = make_catalog(
            {
                "app": [(1, {"lib": (5, 5)})],
                "lib": [(1, {}), (2, {})],
            }
        )
        ok, sel = solve(catalog, {"app": (1, 1)})
        assert not ok
        assert sel == {}

    def test_lexicographic_max_vector(self):
        # 名字序：a < b < c。b 不可达记 0；a、c 取最大可行版本。
        catalog = make_catalog(
            {
                "a": [(1, {"c": (1, 2)}), (3, {"c": (1, 2)})],
                "b": [(9, {})],
                "c": [(1, {}), (2, {})],
            }
        )
        ok, sel = solve(catalog, {"a": (1, 3)})
        assert ok
        assert sel == {"a": 3, "c": 2}

    def test_lexicographic_prefers_earlier_package(self):
        # a 取 2 时 c 只能为 1；a 取 1 时 c 可为 2。字典序最大应选 a=2。
        catalog = make_catalog(
            {
                "a": [(1, {"c": (2, 2)}), (2, {"c": (1, 1)})],
                "c": [(1, {}), (2, {})],
            }
        )
        ok, sel = solve(catalog, {"a": (1, 2)})
        assert ok
        assert sel == {"a": 2, "c": 1}

    def test_diamond_intersection(self):
        catalog = make_catalog(
            {
                "app": [(1, {"x": (1, 3), "y": (1, 1)})],
                "x": [(1, {}), (2, {}), (3, {})],
                "y": [(1, {"x": (2, 2)})],
            }
        )
        ok, sel = solve(catalog, {"app": (1, 1)})
        assert ok
        assert sel == {"app": 1, "x": 2, "y": 1}

    def test_multiple_roots(self):
        catalog = make_catalog(
            {
                "a": [(1, {}), (2, {})],
                "b": [(1, {"a": (2, 2)})],
            }
        )
        ok, sel = solve(catalog, {"a": (1, 2), "b": (1, 1)})
        assert ok
        assert sel == {"a": 2, "b": 1}

    def test_optional_dependency_avoids_package(self):
        # app@1 无依赖、app@2 依赖 lib；字典序最大选 app=2 则 lib 可达
        catalog = make_catalog(
            {
                "app": [(1, {}), (2, {"lib": (1, 1)})],
                "lib": [(1, {})],
            }
        )
        ok, sel = solve(catalog, {"app": (1, 2)})
        assert ok
        assert sel == {"app": 2, "lib": 1}


class TestDifferential:
    """随机生成小规模目录，与暴力枚举对拍。"""

    def test_random_against_brute_force(self):
        rng = random.Random(20260927)
        for case in range(400):
            n = rng.randint(1, 5)
            names = [f"p{i}" for i in range(n)]
            catalog = {}
            for name in names:
                k = rng.randint(1, 4)
                vs = rng.sample(range(1, 6), k)
                items = []
                for v in vs:
                    deps = {}
                    for d in names:
                        if rng.random() < 0.35:
                            lo = rng.randint(1, 4)
                            hi = rng.randint(lo, 5)
                            deps[d] = (lo, hi)
                    items.append({"version": v, "dependencies": deps})
                catalog[name] = items
            roots = {}
            for r in rng.sample(names, rng.randint(1, n)):
                lo = rng.randint(1, 4)
                hi = rng.randint(lo, 5)
                roots[r] = (lo, hi)

            expected = brute_force(catalog, roots)
            got = solve(catalog, roots)
            assert got == expected, f"case {case}: {got} != {expected}"
