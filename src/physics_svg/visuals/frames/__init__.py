from physics_svg.visuals.frames.model import FramesSpec
from physics_svg.visuals.frames.render import render
from physics_svg.visuals.registry import register

register(
    tag="frames",
    title="Системы отсчёта",
    model=FramesSpec,
    render=render,
    module=__name__,
)

__all__ = ["FramesSpec", "render"]
