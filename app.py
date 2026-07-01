from flask import Flask, render_template
from config import Config
from database.db import db
from models.user import User
from routes.auth import auth
from flask_login import LoginManager
from models.subscription import Subscription


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

app.register_blueprint(auth)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

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
