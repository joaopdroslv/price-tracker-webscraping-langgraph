from typing import Any, Dict

from fastapi import FastAPI

app = FastAPI()


@app.route("/ping", methods=["GET"])
def root() -> Dict[str, Any]:
    """Route for testing wheter the API is running or not."""

    return {"answer": "pong"}
