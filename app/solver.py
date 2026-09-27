"""离线软件依赖求解器（与 Web 框架无关的纯函数核心）。

输入：
- catalog: 包名 -> 该包全部候选版本（每项 {"version": int, "dependencies": {包名: [min, max]}}）
- roots:  根包名 -> 闭区间 [min, max]

仅选择从 roots 沿“所选版本”的依赖可达的包，每包恰选一个版本，
满足所有根约束与传递依赖约束；允许可满足的循环依赖。
多解时按全部 catalog 包名排序的版本向量（未选包记 0）取字典序最大者。
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

Interval = Tuple[int, int]
Catalog = Mapping[str, List[Mapping[str, Any]]]


def _max_vector(
    best: Optional[Tuple[int, ...]], cand: Tuple[int, ...]
) -> Tuple[int, ...]:
    if best is None or cand > best:
        return cand
    return best


def solve(
    catalog: Catalog,
    roots: Mapping[str, Interval],
) -> Tuple[bool, Dict[str, int]]:
    """返回 (satisfiable, selected)。

    selected 只包含真正被选择（从根可达）的包，包名排序输出。
    无解时返回 (False, {})。
    """
    names = sorted(catalog)
    # 每个包的可用版本（去重输入已在 API 层保证；这里再保险去重一次，保留首次出现顺序）
    versions_of: Dict[str, List[int]] = {}
    deps_of: Dict[Tuple[str, int], Dict[str, Interval]] = {}
    for name in names:
        seen = set()
        versions_of[name] = []
        for item in catalog[name]:
            v = int(item["version"])
            if v not in seen:
                seen.add(v)
                versions_of[name].append(v)
            deps_of[name, v] = {
                dep: (int(rng[0]), int(rng[1]))
                for dep, rng in item.get("dependencies", {}).items()
            }

    n = len(names)
    # 每个包累积的所有约束区间（来自 root 及各已选父包）
    initial_constraints: Dict[str, List[Interval]] = {
        name: [roots[name]] for name in roots
    }

    # 状态用元组/冻结结构传递，便于回溯：
    # assigned: (name -> version)
    # constraints: (name -> list[(lo, hi)])
    # pending: 已被要求但尚未选版的包名集合
    def dfs(
        assigned: Dict[str, int],
        constraints: Dict[str, List[Interval]],
        pending: List[str],
        best: Optional[Tuple[int, ...]],
    ) -> Optional[Tuple[int, ...]]:
        if not pending:
            # 所有可达包均已选版且区间闭合 => 得到一个可行解
            vec = tuple(assigned.get(name, 0) for name in names)
            return _max_vector(best, vec)

        pkg = pending[0]
        rest = pending[1:]
        active = [rng for rng in constraints.get(pkg, [])]

        for v in versions_of[pkg]:
            if any(v < lo or v > hi for lo, hi in active):
                continue

            new_assigned = dict(assigned)
            new_assigned[pkg] = v
            new_constraints = {k: list(val) for k, val in constraints.items()}
            new_pending = list(rest)

            for dep, rng in deps_of[pkg, v].items():
                if dep in new_assigned:
                    dv = new_assigned[dep]
                    if dv < rng[0] or dv > rng[1]:
                        break  # 已选版本不满足新约束
                    continue
                new_constraints.setdefault(dep, []).append(rng)
                if dep not in new_pending:
                    new_pending.append(dep)
            else:
                best = dfs(new_assigned, new_constraints, new_pending, best)
                continue
            # break 落到这里：该候选版本与既有选择冲突，尝试下一版本
            continue

        return best

    # roots 中不同包约束相同包的情形（root 键本身即包名，互不相同），
    # pending 初始为根集合
    best = dfs({}, initial_constraints, list(roots.keys()), None)

    if best is None:
        return False, {}
    selected = {name: val for name, val in zip(names, best) if val != 0}
    return True, selected
