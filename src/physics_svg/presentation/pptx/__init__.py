"""The lesson as a PowerPoint deck.

The second emitter of the presentation genre, and the one that replaces the
player (docs/pptx.md). It stands where the player stands — over the same
slide models, the same illustrations, the same parsed author text — and
differs only in what it writes at the end.

The layering rule holds: nothing above `presentation/` is imported here, and
the drawing library is used the way the document's Word backend uses it.
"""

from physics_svg.presentation.pptx import design, layouts
from physics_svg.presentation.pptx.package import build_pptx
from physics_svg.presentation.pptx.slide import Slide, slide

__all__ = ["Slide", "build_pptx", "design", "layouts", "slide"]
