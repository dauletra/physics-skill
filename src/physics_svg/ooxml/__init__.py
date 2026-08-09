"""What a .docx and a .pptx have in common: XML text and the OPC container.

Both genres of the skill end in an Office file, and both write it by hand —
the package must work offline, with no pip and no dependency (CLAUDE.md).
What is shared between them is here so that the second backend inherits the
first one's hard-won details rather than rediscovering them: escaping that
Office accepts, a zip that is byte for byte the same on every build, and the
maths — OMML is Office's, not Word's, and a sheet and a slide write a
fraction with the same elements.

Nothing here knows a vocabulary of one format. `w:` belongs to the Word
backend, `p:` to the presentation one; `m:` belongs to both, which is the
whole reason `omml.py` moved in.
"""

from physics_svg.ooxml.element import el, escape
from physics_svg.ooxml.omml import MATH_FONT, convert
from physics_svg.ooxml.package import (
    CORE_PROPERTIES_REL,
    CORE_PROPERTIES_TYPE,
    OFFICE_RELS,
    PACKAGE_RELS,
    Part,
    content_types,
    core_properties,
    relationships,
    zip_package,
)

__all__ = [
    "CORE_PROPERTIES_REL",
    "CORE_PROPERTIES_TYPE",
    "OFFICE_RELS",
    "MATH_FONT",
    "PACKAGE_RELS",
    "Part",
    "content_types",
    "convert",
    "core_properties",
    "el",
    "escape",
    "relationships",
    "zip_package",
]
