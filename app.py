import os
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_jwt_extended import JWTManager

from config import Config
from database.db import db
from logging_config.logger import log_request_data, logger
from middleware.auth import current_user, resolve_current_user
from models.subscription import Subscription
from models.user import User
from routes.api import api
from exceptions.error_handlers import register_error_handlers
from routes.auth import auth
from routes import subscription  # noqa: F401


from utils.currency import format_inr

app = Flask(__name__)
app.config.from_object(Config)

app.jinja_env.filters['inr'] = format_inr
app.jinja_env.globals['format_inr'] = format_inr

db.init_app(app)

# JWT authentication is active across all endpoints and web pages.
jwt = JWTManager(app)

@app.before_request
def load_logged_in_user():
    resolve_current_user()

@app.context_processor
def inject_current_user():
    return dict(current_user=current_user)


from middleware.rate_limiter import limiter
limiter.init_app(app)



@jwt.unauthorized_loader
def unauthorized_loader(callback):
    logger.warning("Unauthorized JWT access attempted for %s", request.path)
    return jsonify({"success": False, "message": "Missing or invalid token"}), 401


@jwt.invalid_token_loader
def invalid_token_loader(callback):
    logger.warning("Invalid JWT token used for %s", request.path)
    return jsonify({"success": False, "message": "Invalid token"}), 401


@jwt.expired_token_loader
def expired_token_loader(jwt_header, jwt_payload):
    logger.warning("Expired JWT token used for %s", request.path)
    return jsonify({"success": False, "message": "Token has expired"}), 401


app.register_blueprint(auth)
app.register_blueprint(api, url_prefix="/api")
register_error_handlers(app)
log_request_data(app)
logger.info("Application startup complete")

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/favicon.ico')
def favicon():
    images_dir = os.path.join(app.root_path, 'static', 'images')
    if os.path.exists(os.path.join(images_dir, 'favicon.ico')):
        return send_from_directory(images_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

