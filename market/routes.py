from market import app, db, bcrypt, mail
from flask import render_template, redirect, url_for, flash, request
from market.models import Stock, User
from market.forms import (RegisterForm, LoginForm, PurchaseStockForm, 
                            SellStockForm, RequestResetForm, ResetPasswordForm)
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
import json
import plotly.express as px
import yfinance as yf
from keras.models import load_model
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
pd.options.plotting.backend = "plotly"


@app.route("/")
@app.route("/home")
def home_page():
    return render_template('home.html', page='home')

@app.route("/profile")
def profile_page():
    return render_template('profile.html', page='profile')

@app.route("/stock")
@login_required
def stock_page():
    return render_template('stock.html', page='stock')

@app.route('/market', methods=['GET', 'POST'])
@login_required
def market_page():
    purchase_form = PurchaseStockForm()
    selling_form = SellStockForm()
    if request.method == "POST":
        #Purchase Stock Logic
        purchased_Stock = request.form.get('purchased_Stock')
        p_Stock_object = Stock.query.filter_by(name=purchased_Stock).first()
        if p_Stock_object:
            if current_user.can_purchase(p_Stock_object):
                p_Stock_object.buy(current_user)
                flash(f"Congratulations! You purchased the {p_Stock_object.name} stock for {p_Stock_object.price}$", category='success')
            else:
                flash(f"Unfortunately, you don't have enough money to purchase the {p_Stock_object.name} stock!", category='danger')
        #Sell Stock Logic
        sold_Stock = request.form.get('sold_Stock')
        s_Stock_object = Stock.query.filter_by(name=sold_Stock).first()
        if s_Stock_object:
            if current_user.can_sell(s_Stock_object):
                s_Stock_object.sell(current_user)
                flash(f"Congratulations! You sold {s_Stock_object.name} stock back to market!", category='success')
            else:
                flash(f"Something went wrong with selling {s_Stock_object.name} stock", category='danger')


        return redirect(url_for('market_page'))

    if request.method == "GET":
        stocks = Stock.query.filter_by(owner=None)
        owned_stocks = Stock.query.filter_by(owner=current_user.id)
        return render_template('market.html', stocks=stocks, purchase_form=purchase_form, owned_stocks=owned_stocks, selling_form=selling_form)

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        user_to_create = User(username=form.username.data, 
                              email=form.email.data, 
                              password=form.password1.data)
        db.session.add(user_to_create)
        db.session.commit()
        login_user(user_to_create)
        flash(f"Account created successfully! You are now logged in as {user_to_create.username}", category='success')
        return redirect(url_for('market_page'))
    if form.errors != {}: #If there are errors from the form submission (not from the validations)
        for err_msg in form.errors.values():
            flash(f'There was an error with creating a new user: {err_msg}', category='danger')
    return render_template('register.html', form=form, page='register')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(username=form.username.data).first()
        if attempted_user and attempted_user.check_password_correction(
                attempted_password=form.password.data
        ):
            login_user(attempted_user)
            flash(f'Success! You are logged in as: {attempted_user.username}', category='success')
            return redirect(url_for('market_page'))
        else:
            flash('Username and password are not match! Please try again', category='danger')
    return render_template('login.html', form=form, page='login')

@app.route('/logout')
def logout_page():
    logout_user()
    flash("You have been logged out!", category='info')
    return redirect(url_for("home_page"))


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='boukhrisssaber@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home_page'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', category='info')
        return redirect(url_for('login_page'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', category='warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', category='success')
        return redirect(url_for('login_page'))
    return render_template('reset_token.html', title='Reset Password', form=form)

@app.route('/callback/<endpoint>')
def cb(endpoint):   
    if endpoint == "getStock":
        return gm(request.args.get('data'),request.args.get('period'),request.args.get('interval'))
    elif endpoint == "getInfo":
        stock = request.args.get('data')
        st = yf.Ticker(stock)
        return json.dumps(st.info)
    else:
        return "Bad endpoint", 400

@app.route('/precall/<endpoint>')
def pc(endpoint):
    if endpoint == "display":
        return display(request.args.get('data'))
    else:
        return "Bad endpoint", 400

# Return the JSON data for the Plotly graph
def gm(stock,period, interval):
    st = yf.Ticker(stock)
  
    # Create a line graph
    df = st.history(period=(period), interval=interval)
    df['Date']=df.index
    df=df.reset_index(drop=True)
    predict = df
    max = (predict.max())
    min = (predict.min())
    rangey = max - min
    margin = rangey * 0.05
    max = max + margin
    min = min - margin
    fig = px.area(df, x='Date', y="Close",
    hover_data=("Open","Close","Volume"), 
    range_y=(min,max), template="seaborn" )

    # Create a JSON representation of the graph
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

def display(stock):
    
    st = yf.Ticker(stock)
    df = st.history(period='Max')
    df=df.reset_index()
     #Define variables and splitinig the data to training and testing sets
    d=30

    n=int(df.shape[0]*0.85)
    test_set = df.iloc[n:, 1:2].values
    # load model
    model = load_model('lstmmodel.h5')
    # Getting the predicted stock price
    sc = MinMaxScaler(feature_range = (0, 1))
    test_set = sc.fit_transform(test_set)
    dataset_train = df.iloc[:n, 1:2]
    dataset_test = df.iloc[n:, 1:2]
    dataset_total = pd.concat((dataset_train, dataset_test), axis = 0)
    inputs = dataset_total[len(dataset_total) - len(dataset_test) - d:].values
    inputs = inputs.reshape(-1,1)
    inputs = sc.transform(inputs)
    #Reshaping data and finalizing
    X_test = []
    for i in range(d, inputs.shape[0]):
        X_test.append(inputs[i-d:i, 0])
    X_test = np.array(X_test)
    X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
    predicted_stock_price = model.predict(X_test)
    predicted_stock_price = sc.inverse_transform(predicted_stock_price)

    df['Date']=df.index
    df=df.reset_index(drop=True)

    predict = df

    max = (predict.max())
    min = (predict.min())
    rangey = max - min
    margin = rangey * 0.05
    max = max + margin
    min = min - margin

    print('Something')
    plt.plot(predict.loc[n:, 'Date'],dataset_test.values, color = 'red', label = stock +' Real Stock Price')
    plt.plot(predict.loc[n:, 'Date'],predicted_stock_price, color = 'blue', label = stock +' Predicted Stock Price')

    # Create a line graph
    plt.title('Price Prediction Figure')
    plt.xlabel('Time')
    plt.ylabel(stock +'stock Price')
    plt.legend()
    plt.xticks(rotation=90)
    plt.style.use('seaborn')
    plt.show()
    return(True)
