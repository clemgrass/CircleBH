"""Configuración común de los tests.

Perfiles de Hypothesis (ADR 0007):
- `default`: el de siempre, con ejemplos al azar. Lo usa `poe fast`.
- `ci`: determinista y sin límite de tiempo por ejemplo. Lo usan `poe check` y la CI.
"""

import os

from hypothesis import settings

settings.register_profile("ci", derandomize=True, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))
