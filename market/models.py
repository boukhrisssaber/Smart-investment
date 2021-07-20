from flask import flash, abort, redirect, url_for
from market import app, db, login_manager
from market import bcrypt
from flask_login import UserMixin, current_user, AnonymousUserMixin
from market import admin
from flask_admin.contrib.sqla import ModelView
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin, AnonymousUserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(length=30), nullable=False, unique=True)
    email = db.Column(db.String(length=50), nullable=False, unique=True)
    password_hash = db.Column(db.String(length=60), nullable=False)
    budget = db.Column(db.Integer(), nullable=False, default=1000)
    is_admin = db.Column(db.Boolean(), nullable=False, default=False)
    stocks = db.relationship('Stock', backref='owned_user', lazy=True)

    @property
    def prettier_budget(self):
        if len(str(self.budget)) >= 4:
            return f'{str(self.budget)[:-3]},{str(self.budget)[-3:]}$'
        else:
            return f"{self.budget}$"

    @property
    def password(self):
        return self.password

    @password.setter
    def password(self, plain_text_password):
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self, attempted_password):
        return bcrypt.check_password_hash(self.password_hash, attempted_password)

    def can_purchase(self, Stock_obj):
        return self.budget >= Stock_obj.price

    def can_sell(self, Stock_obj):
        return Stock_obj in self.stocks

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

class Stock(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(length=30), nullable=False, unique=True)
    Ticker = db.Column(db.String(length=12), nullable=False, unique=True)
    price = db.Column(db.Integer(), nullable=False)
    description = db.Column(db.String(length=1024), nullable=False, unique=True)
    owner = db.Column(db.Integer(), db.ForeignKey('user.id'))
    def __repr__(self):
        return f'Stock {self.name}'

    def buy(self, user):
        self.owner = user.id
        user.budget -= self.price
        db.session.commit()

    def sell(self, user):
        self.owner = None
        user.budget += self.price
        db.session.commit()


class StockData(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    symbol = db.Column(db.String(), nullable=False, unique=True)
    data = db.Column(db.String(), nullable=False, unique=True)

class controller (ModelView):
    def is_accessible(self):
        if current_user.is_authenticated==False:
            return abort(403)
        elif current_user.is_admin == True:
            return current_user.is_authenticated
        else:
            return abort(404)


admin.add_view (controller(User, db.session))
admin.add_view (controller(Stock, db.session))
admin.add_view (controller(StockData, db.session))