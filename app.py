import os
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_jwt_extended import JWTManager
from flask_login import LoginManager

from config import Config
from database.db import db
from logging_config.logger import log_request_data, logger
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

# Flask-Login remains active for server-rendered HTML pages.
login_manager = LoginManager()
login_manager.init_app(app)
setattr(login_manager, "login_view", "auth.login")

# JWT is enabled alongside Flask-Login for future REST API usage.
jwt = JWTManager(app)

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

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
