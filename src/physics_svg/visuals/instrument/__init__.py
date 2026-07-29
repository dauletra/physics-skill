from physics_svg.visuals.instrument.model import InstrumentSpec
from physics_svg.visuals.instrument.render import render
from physics_svg.visuals.registry import register

register(
    tag="instrument",
    title="Приборы со шкалой",
    model=InstrumentSpec,
    render=render,
    module=__name__,
)

__all__ = ["InstrumentSpec", "render"]
