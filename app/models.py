"""请求/响应模型与输入校验（非法输入由 FastAPI 自动返回 422）。"""

from __future__ import annotations

from typing import Annotated, Dict, List, Tuple

from pydantic import AfterValidator, BaseModel, Field, model_validator

# 严格正整数：拒绝 bool / 浮点 / 字符串冒充
PosInt = Annotated[int, Field(strict=True, ge=1)]


def _check_interval(rng: Tuple[int, int]) -> Tuple[int, int]:
    lo, hi = rng
    if lo > hi:
        raise ValueError(f"非法区间 [{lo}, {hi}]：min 不能大于 max")
    return rng


# 形如 [min, max] 的正整数闭区间，min <= max；长度不为 2 同样校验失败
Interval = Annotated[
    Tuple[PosInt, PosInt],
    AfterValidator(_check_interval),
]


class VersionItem(BaseModel):
    version: PosInt
    dependencies: Dict[str, Interval] = Field(default_factory=dict)


class SolveRequest(BaseModel):
    catalog: Dict[str, List[VersionItem]]
    roots: Dict[str, Interval] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_cross_fields(self) -> "SolveRequest":
        errors: List[str] = []

        if not (1 <= len(self.catalog) <= 8):
            errors.append("catalog 必须包含 1～8 个包")

        known = set(self.catalog)

        for name, items in self.catalog.items():
            if not name:
                errors.append("包名不能为空")
            if not (1 <= len(items) <= 5):
                errors.append(f"包 {name!r} 必须包含 1～5 个版本")
            seen: set[int] = set()
            for item in items:
                if item.version in seen:
                    errors.append(f"包 {name!r} 存在重复版本 {item.version}")
                seen.add(item.version)
                for dep in item.dependencies:
                    if dep not in known:
                        errors.append(
                            f"包 {name!r}@{item.version} 依赖未知包 {dep!r}"
                        )

        for name in self.roots:
            if not name:
                errors.append("roots 中包名不能为空")
            elif name not in known:
                errors.append(f"roots 引用未知包 {name!r}")

        if errors:
            raise ValueError(errors)
        return self


class SolveResponse(BaseModel):
    satisfiable: bool
    selected: Dict[str, int]
