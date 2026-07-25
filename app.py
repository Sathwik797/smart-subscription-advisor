from flask import Flask, jsonify, render_template, request
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


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Flask-Login remains active for server-rendered HTML pages.
login_manager = LoginManager()
login_manager.init_app(app)
setattr(login_manager, "login_view", "auth.login")

# JWT is enabled alongside Flask-Login for future REST API usage.
jwt = JWTManager(app)


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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app.run(debug=True)
