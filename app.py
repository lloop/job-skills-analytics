"""Optional Flask dashboard entry point."""

from flask import Flask

app = Flask(__name__)


@app.get("/")
def index() -> str:
    return "Job Skills Analytics"


if __name__ == "__main__":
    app.run(debug=True)
