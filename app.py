# app.py - Main Application Entry Point
from flask import Flask
import os
from dotenv import load_dotenv
from User.routes import routes
from flask_mail import Mail

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
# Mail Setup (for counselor–student communication)
# --------------------------------------------------
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 587))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False

# Initialize Flask-Mail
mail = Mail(app)

# --------------------------------------------------
# Register Blueprints
# --------------------------------------------------
app.register_blueprint(routes)


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == '__main__':
    # debug=True is for local development ONLY.
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)
