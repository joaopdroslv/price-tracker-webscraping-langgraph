from typing import Any, Dict

from fastapi import FastAPI

app = FastAPI()


@app.get("/ping")
def ping() -> Dict[str, Any]:
    """Route for testing wheter the API is running or not."""

    return {"reply": "pong"}
