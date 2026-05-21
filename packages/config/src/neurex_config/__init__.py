"""Neurex QA — shared pydantic-settings base configuration.

Each service extends BaseServiceSettings with its own fields.

Usage:
    from neurex_config import BaseServiceSettings

    class MySettings(BaseServiceSettings):
        MY_FEATURE_FLAG: bool = False

    settings = MySettings()
"""

from neurex_config._base import BaseServiceSettings

__all__ = ["BaseServiceSettings"]
