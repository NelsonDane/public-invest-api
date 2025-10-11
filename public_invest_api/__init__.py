"""Fennel Invest API.

An unofficial API for interacting with Fennel.com's Invest platform.
"""

import public_invest_api.models.com.hellopublic.userapigateway.api.rest as models
from public_invest_api.public import Public

__all__ = ["Public", "models"]
