"""Система автоматизации подготовки курсовых и дипломных работ.

Публичный API:

.. code-block:: python

    from diploma.settings import Settings
    from diploma.pipeline import run_pipeline

    result = run_pipeline(Settings(topic="...", out_dir="build/demo"))
    print(result.files["DOCX"], result.files["PDF"])
"""

__version__ = "1.0.0"

__all__ = ["Settings", "run_pipeline", "__version__"]

from .pipeline import run_pipeline  # noqa: E402
from .settings import Settings  # noqa: E402
