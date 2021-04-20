from flask import Flask, url_for, request, render_template, redirect, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
import sqlalchemy
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_forms import *
import random


app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/blogs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
roles = ['customer', 'admin']
basket_count = 0
app.add_template_global(name='basket_count', f=basket_count)

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

@app.context_processor
def inject_user():
    return dict(basket_count=basket_count)

@app.route('/')
def mainpage():
    update_basket()
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
        item = Item(title=request.form['name'], price=request.form['price'], image=request.form['image'])
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

class Recept(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer) #, db.ForeignKey('item.id'))
    about = db.Column(db.Text)
    recept = db.Column(db.Text)

class Basket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    user_id = db.Column(db.Integer)
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

@app.route('/menu', methods=['GET', 'POST'])
def menu():
    items = Item.query.order_by(-Item.isActive, Item.title).all()
    if request.method == "POST":
        if not current_user.is_anonymous:
            print('append in basket')
            id = request.form['id']
            item = Item.query.get(id)
            is_in_basket = Basket.query.filter_by(name=item.title).first()
            print(is_in_basket)
            if is_in_basket == None:
                print(item)
                basket = Basket()
                basket.name = item.title
                basket.user_id = current_user.id
                basket.about = item.about
                basket.count = 1
                basket.price = item.price
                db.session.add(basket)
            else:
                is_in_basket.count += 1
            db.session.commit()
            update_basket()
        else:
            return 'для использования корзины необходимо авторизоваться\n<p><a href="auth">Авторизоваться</a></p>'
    return render_template("menu.html", items=items, recept=Recept.query.all())

@app.route('/users', methods=['GET', 'POST'])
def users():
    users = User.query.all()
    print(users)
    baskets = Basket.query.all()
    for i in range(1, len(baskets) + 3):
        s = 'btn' + str(i)
        r = request.form.get(s)
        print(r)
        if r == '+':
            print('plus')
            basket = Basket.query.filter_by(user_id=current_user.id, id=i).first()
            basket.count += 1
    return render_template("users.html", data=users)

@app.route('/calc', methods=['GET', 'POST'])
def calc():
    return render_template("deliveryCalculaor.html")

@app.route('/ordering', methods=['GET', 'POST'])
def ordering():
    form = OrderForm()
    items = Basket.query.filter_by(user_id=current_user.id).all()
    update_basket()
    summa = 0
    for elem in items:
        summa += elem.price * elem.count
    return render_template("ordering.html", summa=summa, form=form)

@app.route('/basket', methods=['GET', 'POST'])
def basket():
    baskets = Basket.query.all()
    for i in range(1, len(baskets) + 3):
        s = 'btn' + str(i)
        r = request.form.get(s)
        print(r)
        if r == '+':
            print('plus')
            basket = Basket.query.filter_by(user_id=current_user.id, id=i).first()
            basket.count += 1
        elif r == '-':
            print('minus')
            basket = Basket.query.get(i)
            basket.count -= 1
        d = 'del' + str(i)
        r = request.form.get(d)
        if r == 'Удалить':
            basket = Basket.query.get(i)
            db.session.delete(basket)
    db.session.commit()
    if request.form.get("btn") == "Оформить заказ":
        return redirect('/ordering')
    elif request.form.get("btn") == "Очистить корзину":
        basket = Basket.query.all()
        for elem in basket:
            db.session.delete(elem)
        db.session.commit()
    items = Basket.query.filter_by(user_id=current_user.id).all()
    update_basket()
    summa = 0
    for elem in items:
        summa += elem.price * int(elem.count)
    return render_template("basket.html", data=items, summa=summa)

def update_basket():
    count = Basket.query.filter_by(user_id=current_user.id).all()
    global basket_count
    basket_count = len(count)

if __name__ == '__main__':
    app.debug = True
    app.run()
