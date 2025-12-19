import os

import reflex as rx

config = rx.Config(
    app_name="chatakon_front",
    api_url=os.getenv("REFLEX_API_URL", "http://localhost:8000"),
    frontend_port=3000,
    backend_port=8000,
    frontend_host="0.0.0.0",
    backend_host="0.0.0.0",
    show_built_with_reflex=False,
)
