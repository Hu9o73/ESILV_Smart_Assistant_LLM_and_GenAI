import os

import reflex as rx

config = rx.Config(
    app_name="chatakon_front",
    agentic_api_url="http://chatakon-agentic:8001",
    cors_allowed_origins=["http://localhost:3000", "http://localhost:8091", "https://chatakon.fr"],
    show_built_with_reflex=False,
)
