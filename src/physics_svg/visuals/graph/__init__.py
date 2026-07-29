from physics_svg.visuals.graph.model import GraphSpec, SeriesSpec
from physics_svg.visuals.graph.render import render
from physics_svg.visuals.registry import register

register(
    tag="graph",
    title="График",
    model=GraphSpec,
    render=render,
    module=__name__,
)

__all__ = ["GraphSpec", "SeriesSpec", "render"]
