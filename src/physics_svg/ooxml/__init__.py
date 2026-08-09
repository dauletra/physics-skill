"""What a .docx and a .pptx have in common: XML text and the OPC container.

Both genres of the skill end in an Office file, and both write it by hand —
the package must work offline, with no pip and no dependency (CLAUDE.md).
What is shared between them is exactly two things, and they are here so that
the second backend inherits the first one's hard-won details rather than
rediscovering them: escaping that Office accepts, and a zip that is byte
for byte the same on every build.

Nothing here knows a vocabulary. `w:` belongs to the Word backend, `p:` to
the presentation one.
"""

from physics_svg.ooxml.element import el, escape
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
    "PACKAGE_RELS",
    "Part",
    "content_types",
    "core_properties",
    "el",
    "escape",
    "relationships",
    "zip_package",
]
