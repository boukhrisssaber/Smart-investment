from os import environ as env
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_admin import Admin
from flask_mail import Mail

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market.db'
app.config['SECRET_KEY'] = 'd7e44ed564a4a2e699c6e4f1'

admin = Admin(app)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)

login_manager.login_view = "login_page"
login_manager.login_message_category = "info"

app.config.update(
MAIL_SERVER='smtp.hushmail.com',
MAIL_PORT='587',
MAIL_USE_TLS=True,
MAIL_USERNAME='boukhrisssaber@gmail.com',#env['EMAIL_USER']'',
MAIL_PASSWORD='Arcwave13',#env['EMAIL_PASS'])
)
mail = Mail(app)

from market import routes