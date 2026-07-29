from physics_svg.visuals.registry import register
from physics_svg.visuals.vectors.model import AngleSpec, ArrowSpec, VectorsSpec
from physics_svg.visuals.vectors.render import render

register(
    tag="vectors",
    title="Векторные диаграммы",
    model=VectorsSpec,
    render=render,
    module=__name__,
)

__all__ = ["AngleSpec", "ArrowSpec", "VectorsSpec", "render"]
