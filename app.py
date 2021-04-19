from flask import Flask, url_for, request, render_template, redirect, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
import sqlalchemy
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_forms import *


app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/blogs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
roles = ['customer', 'admin']

@login_manager.user_loader
def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    role = sqlalchemy.Column(sqlalchemy.String, default='customer')
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)

@app.route('/')
def mainpage():
    return render_template('index.html', title='Главная')

@app.route('/profile')
@login_required
def profile():
    print(current_user.role)
    if current_user.role == 'admin':
        return render_template('profile_adm.html', title='Профиль', data=current_user)
    else:
        return render_template('profile_user.html', title='Профиль', data=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/auth')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html', title='Контакты')

@app.route('/additem', methods=['GET', 'POST'])
@login_required
def additem():
    form = AddItemForm()
    if request.method == "POST":
        print(request.form['name'])
        item = Item(title=request.form['name'], price=request.form['price'])
        db.session.add(item)
        db.session.commit()
        return redirect('/menu')
    else:
        return render_template('additem.html', title='Профиль', form=form)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    image = db.Column(db.Text, default="jpg.jpg")
    price = db.Column(db.Integer, nullable=False)
    about = db.Column(db.Text)
    recept_id = db.Column(db.Integer, default=0)
    isActive = db.Column(db.Boolean, default=True)
    def __repr__(self):
        return self.title

class Recept(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer) #, db.ForeignKey('item.id'))
    about = db.Column(db.Text)
    recept = db.Column(db.Text)

class Basket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    about = db.Column(db.String)
    count = db.Column(db.Integer, default=1)
    price = db.Column(db.Integer)

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    form = LoginForm()
    if request.method == "POST":
        name = request.form['username']
        print(name)
        user = User.query.filter_by(name=name).first()
        if user and check_password_hash(user.hashed_password, request.form["password"]):
            print("Вы авторизовались")
            rm = True if request.form.get('remainme') else False
            login_user(user, remember =rm)
            return f'успешно авторизовались в аккаунте {name}\n<p><a href="profile">Перейти в профиль</a></p>'
        else:
            return 'ошибка авторизации'
    else:
        return render_template('login.html', title='Авторизация', form=form)

@app.route('/reg', methods=['GET', 'POST'])
def reg():
    form = LoginForm()
    if form.validate_on_submit():
        user = User(name=request.form['username'], hashed_password=generate_password_hash(request.form['password']))
        db.session.add(user)
        db.session.commit()
        print(f'success {request.form["username"]}')
        return render_template('successful_reg.html', title='Успех :)')
    else:
        return render_template('registration.html', title='Регистрация', form=form)

@app.route('/menu')
def menu():
    items = Item.query.order_by(-Item.isActive, Item.title).all()  # , Item.price
    print(items)
    return render_template("menu.html", items=items, recept=Recept.query.all())

@app.route('/users', methods=['GET', 'POST'])
def users():
    users = User.query.all()
    print(users)
    return render_template("users.html", data=users)


if __name__ == '__main__':
    app.debug = True
    app.run()
