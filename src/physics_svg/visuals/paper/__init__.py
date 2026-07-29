from physics_svg.visuals.paper.model import PaperSpec
from physics_svg.visuals.paper.render import render
from physics_svg.visuals.registry import register

register(
    tag="paper",
    title="Бумага",
    model=PaperSpec,
    render=render,
    module=__name__,
)

__all__ = ["PaperSpec", "render"]
