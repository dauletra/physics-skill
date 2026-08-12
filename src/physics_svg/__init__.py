"""Physics illustration library and document builder.

Layers, strictly bottom-up (no reverse imports):

    draw      -> canvas, geometry, transforms, styles; knows no physics
    elements  -> physical vocabulary built on draw (arrows, surfaces, bodies)
    schema    -> declarative validation kernel and JSON Schema emission
    visuals   -> the illustration library: one package per type
    document  -> blocks, questions, answers section, HTML assembly
    cli       -> single entry point with subcommands

See docs/architecture.md for the rationale behind the split.
"""

__version__ = "0.6.1+dev"
