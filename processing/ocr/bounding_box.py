from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from core.guards import require


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        require(isinstance(self.x, (int, float)), "x must be a number")
        require(isinstance(self.y, (int, float)), "y must be a number")
        require(isinstance(self.width, (int, float)), "width must be a number")
        require(isinstance(self.height, (int, float)), "height must be a number")
        require(self.x >= 0.0, "x must be >= 0")
        require(self.y >= 0.0, "y must be >= 0")
        require(self.width > 0.0, "width must be > 0")
        require(self.height > 0.0, "height must be > 0")

    @classmethod
    def create(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> BoundingBox:
        return cls(x=x, y=y, width=width, height=height)

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def contains(self, other: BoundingBox) -> bool:
        return (
            self.x <= other.x
            and self.y <= other.y
            and self.x2 >= other.x2
            and self.y2 >= other.y2
        )

    def intersects(self, other: BoundingBox) -> bool:
        return (
            self.x < other.x2
            and self.x2 > other.x
            and self.y < other.y2
            and self.y2 > other.y
        )

    def intersection(self, other: BoundingBox) -> BoundingBox | None:
        ix = max(self.x, other.x)
        iy = max(self.y, other.y)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        if ix2 <= ix or iy2 <= iy:
            return None
        return BoundingBox(x=ix, y=iy, width=ix2 - ix, height=iy2 - iy)

    def union(self, other: BoundingBox) -> BoundingBox:
        ux = min(self.x, other.x)
        uy = min(self.y, other.y)
        ux2 = max(self.x2, other.x2)
        uy2 = max(self.y2, other.y2)
        return BoundingBox(x=ux, y=uy, width=ux2 - ux, height=uy2 - uy)

    def iou(self, other: BoundingBox) -> float:
        inter = self.intersection(other)
        if inter is None:
            return 0.0
        inter_area = inter.area
        union_area = self.area + other.area - inter_area
        if union_area <= 0.0:
            return 0.0
        return inter_area / union_area

    def expand(self, margin_x: float, margin_y: float) -> BoundingBox:
        require(isinstance(margin_x, (int, float)), "margin_x must be a number")
        require(isinstance(margin_y, (int, float)), "margin_y must be a number")
        require(margin_x >= 0.0, "margin_x must be >= 0")
        require(margin_y >= 0.0, "margin_y must be >= 0")
        new_x = max(0.0, self.x - margin_x)
        new_y = max(0.0, self.y - margin_y)
        new_w = self.width + 2 * margin_x
        new_h = self.height + 2 * margin_y
        return BoundingBox(x=new_x, y=new_y, width=new_w, height=new_h)

    def distance_to(self, other: BoundingBox) -> float:
        dx = self.center_x - other.center_x
        dy = self.center_y - other.center_y
        return math.hypot(dx, dy)

    def is_horizontally_aligned(
        self,
        other: BoundingBox,
        tolerance: float = 5.0,
    ) -> bool:
        require(isinstance(tolerance, (int, float)), "tolerance must be a number")
        require(tolerance >= 0.0, "tolerance must be >= 0")
        return abs(self.center_y - other.center_y) <= tolerance

    def is_vertically_aligned(
        self,
        other: BoundingBox,
        tolerance: float = 5.0,
    ) -> bool:
        require(isinstance(tolerance, (int, float)), "tolerance must be a number")
        require(tolerance >= 0.0, "tolerance must be >= 0")
        return abs(self.center_x - other.center_x) <= tolerance

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BoundingBox:
        return cls(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
        )
