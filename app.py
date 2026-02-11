# app.py - Main Application Entry Point
from flask import Flask
import os
from dotenv import load_dotenv
from User.routes import routes

load_dotenv()

# --------------------------------------------------
# App Setup
# --------------------------------------------------
app = Flask(__name__)
secret_key = os.getenv("SECRET_KEY")

# Validation
if not secret_key:
    raise RuntimeError("SECRET_KEY not set in environment variables")
app.secret_key = secret_key

# --------------------------------------------------
# Register Blueprints
# --------------------------------------------------
app.register_blueprint(routes)


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache,"
    "must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == '__main__':
    app.run(debug=True)
