from flask import Flask, request, render_template, redirect
import sqlalchemy
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
import os
from email_sender import send_email
from flask_forms import *
from ya_map import map


app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/blogs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/img/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
login_manager = LoginManager(app)
roles = ['customer', 'admin', 'manager', 'courier', 'chef']
statuses = ['на проверке', 'готовится', 'готов', 'передан в службу доставки', 'выполнен']
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
basket_count = 0
app.add_template_global(name='basket_count', f=basket_count)

try:
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


    class User(UserMixin, db.Model):
        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
        name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
        role = sqlalchemy.Column(sqlalchemy.String, default='customer')
        email = sqlalchemy.Column(sqlalchemy.String)
        hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)


    @app.context_processor
    def inject_user():
        return dict(basket_count=basket_count)


    @app.route('/', methods=['GET', 'POST'])
    def mainpage():
        if not current_user.is_anonymous:
            update_basket()
        return render_template('index.html', title='Главная')


    @app.route('/profile')
    @login_required
    def profile():
        update_basket()
        if current_user.role == 'admin':
            return render_template('profile_adm.html', title='Профиль · Pizza Online', data=current_user)
        else:
            return render_template('profile_user.html', title='Профиль · Pizza Online', data=current_user)


    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect('/auth')


    @app.route('/contacts')
    def contacts():
        if not current_user.is_anonymous:
            update_basket()
        address = "Россия, Санкт - Петербург, Пушкинский\
            район, Павловск, улица\
            Декабристов, 16"
        filename = 'map.png'
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        map(address, path)
        return render_template('contacts.html', title='Контакты · Pizza Online')


    @app.route('/additem', methods=['GET', 'POST'])
    @login_required
    def additem():
        if current_user.role == 'admin' or current_user.role == 'manager' or current_user.role == 'chef':
            form = AddItemForm()
            if request.method == "POST":
                item = Item(title=request.form['name'], price=request.form['price'], image=request.form['image'],
                            about=request.form['about'])
                db.session.add(item)
                db.session.commit()
                return redirect('/menu')
            else:
                return render_template('additem.html', title='Добавление товара · Pizza Online', form=form)
        else:
            return render_template('error.html', error='Ошибка доступа')


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
        item_id = db.Column(db.Integer)
        about = db.Column(db.Text)
        recept = db.Column(db.Text)


    class Order(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        address = db.Column(db.String)
        comment = db.Column(db.Text)
        email = db.Column(db.Text)
        phone = db.Column(db.Text)
        name = db.Column(db.Text)
        status = db.Column(db.Text)
        total = db.Column(db.Integer)


    class OrderItems(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        order_id = db.Column(db.Integer)
        item = db.Column(db.Text)
        count = db.Column(db.Integer, default=1)
        about = db.Column(db.Text)
        price = db.Column(db.Integer, nullable=False)


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
            user = User.query.filter_by(name=name).first()
            if user and check_password_hash(user.hashed_password, request.form["password"]):
                rm = True if request.form.get('remainme') else False
                login_user(user, remember=rm)
                return redirect('/menu')
            else:
                return render_template('error.html', error='ошибка авторизации')
        else:
            return render_template('login.html', title='Авторизация · Pizza Online', form=form)


    @app.route('/reg', methods=['GET', 'POST'])
    def reg():
        form = LoginForm()
        if form.validate_on_submit():
            print(request.form['email'])
            user = User(name=request.form['username'],
                        hashed_password=generate_password_hash(request.form['password']),
                        email=request.form['email'])
            db.session.add(user)
            db.session.commit()
            return redirect('/auth')
        else:
            return render_template('registration.html', title='Регистрация · Pizza Online', form=form)


    @app.route('/menu', methods=['GET', 'POST'])
    def menu():
        items = Item.query.order_by(-Item.isActive, Item.title).all()
        if request.method == "POST":
            if not current_user.is_anonymous:
                idi = request.form['id']
                item = Item.query.get(idi)
                is_in_basket = Basket.query.filter_by(name=item.title, user_id=current_user.id).first()
                print(is_in_basket)
                if is_in_basket is None:
                    print(True)
                    basket_elem = Basket()
                    basket_elem.name = item.title
                    basket_elem.user_id = current_user.id
                    basket_elem.about = item.about
                    basket_elem.count = 1
                    basket_elem.price = item.price
                    db.session.add(basket_elem)
                else:
                    is_in_basket.count += 1
                db.session.commit()
                update_basket()
            else:
                return render_template('error.html', error='для использования корзины необходимо авторизоваться')
        return render_template("menu.html", items=items, recept=Recept.query.all(), title='Меню · Pizza Online')


    @app.route('/users', methods=['GET', 'POST'])
    @login_required
    def users():
        if current_user.role == 'admin' or current_user.role == 'manager':
            if request.method == 'POST':
                idi = request.form['id']
                if request.form.get("del") == "Удалить":
                    user = User.query.get(idi)
                    if user is not None:
                        db.session.delete(user)
                        db.session.commit()
                elif request.form.get("save") == "Сохранить":
                    user = User.query.filter_by(id=idi).first()
                    user.role = request.form['select_role']
                    db.session.commit()
            all_users = User.query.all()
            return render_template("users.html", data=all_users, roles=roles, title='Пользователи · Pizza Online')
        else:
            return render_template('error.html', error='Ошибка доступа')


    @app.route('/orders', methods=['GET', 'POST'])
    @login_required
    def orderd():
        if current_user.role == 'admin' or current_user.role == 'manager' \
                or current_user.role == 'chef' or current_user.role == 'courier':
            orders = Order.query.all()
            return render_template("orders.html", data=orders, title='Заказы · Pizza Online')
        else:
            return render_template('error.html', error='Ошибка доступа')


    @app.route('/my_orders', methods=['GET', 'POST'])
    @login_required
    def morderd():
        orders = Order.query.filter_by(name=current_user.name).all()
        return render_template("my_orders.html", data=orders, title='Мои заказы · Pizza Online')


    @app.route('/my_order', methods=['GET', 'POST'])
    @login_required
    def morder():
        if request.method == "POST":
            idi = request.form['id']
            if request.form.get("open") == "Подробнее":
                my_order = Order.query.get(idi)
                items = Order_items.query.filter_by(order_id=idi).all()
                return render_template("my_order.html", data=my_order, items=items, title='Мой заказ · Pizza Online')


    @app.route('/order', methods=['GET', 'POST'])
    @login_required
    def order():
        if current_user.role == 'admin' or current_user.role == 'manager' or current_user.role == 'chef' \
                or current_user.role == 'courier':
            if request.method == "POST":
                idi = request.form['id']
                if request.form.get("btn") == "Удалить":
                    my_order = Order.query.get(idi)
                    db.session.delete(my_order)
                    db.session.commit()
                    return redirect("/orders")
                elif request.form.get("open") == "Подробнее":
                    my_order = Order.query.filter_by(id=idi).first()
                    items = Order_items.query.filter_by(order_id=idi).all()
                    return render_template("order.html", data=my_order, items=items, statuses=statuses)
                elif request.form.get('save'):
                    my_order = Order.query.get(idi)
                    if my_order.status != request.form['select_status']:
                        try:
                            send_email(my_order.name, my_order.id, my_order.email, str(request.form['select_status']))
                        except Exception:
                            return render_template('error.html', error='неверный статус')
                    my_order.status = request.form['select_status']
                    db.session.commit()
                    return redirect('/orders')
            else:
                return render_template('error.html', error='неверный id заказа')
        else:
            return render_template('error.html', error='Ошибка доступа')


    @app.route('/images', methods=['GET', 'POST'])
    @login_required
    def images():
        if current_user.role == 'admin' or current_user.role == 'manager' or current_user.role == 'chef':
            if request.method == "POST":
                file = request.files['file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            directory = os.path.abspath(__file__).split("\\")[:-1]
            directory.append('static')
            directory.append('img')
            directory = '/'.join(directory)
            files = os.listdir(directory)
            return render_template("images.html", data=files, title='Изображения · Pizza Online')
        else:
            return render_template('error.html', error='Ошибка доступа')


    @app.route('/addimage', methods=['GET', 'POST'])
    @login_required
    def add_image():
        if current_user.role == 'admin' or current_user.role == 'manager' or current_user.role == 'chef':
            return render_template("addimage.html", title='Добавление изображения · Pizza Online')
        else:
            return render_template('error.html', error='Ошибка доступа')


    @app.route('/ordering', methods=['POST', 'GET'])
    @login_required
    def ordering():
        form = OrderForm()
        items = Basket.query.filter_by(user_id=current_user.id).all()
        update_basket()
        summa = 0
        for elem in items:
            summa += elem.price * elem.count
        if request.method == "POST":
            if request.form.get("submit") == "Оформить заказ":
                my_order = Order()
                d_coord = request.form['d_coord']
                d_coord = d_coord.partition(",")[2] + d_coord.partition(",")[1] + d_coord.partition(",")[0]
                my_order.address = geocoder_get_address(d_coord)
                my_order.total = int(request.form['d_cost']) + summa
                my_order.comment = request.form['comment']
                my_order.phone = request.form['phone']
                my_order.status = 'на проверке'
                my_order.name = current_user.name
                print(current_user.email)
                my_order.email = current_user.email
                db.session.add(my_order)
                db.session.commit()
                my_order = Order.query.filter_by(address=geocoder_get_address(d_coord)).first()
                my_basket = Basket.query.filter_by(user_id=current_user.id).all()
                for elem in my_basket:
                    item = Order_items(order_id=my_order.id, item=elem.name, count=elem.count, about=elem.about,
                                       price=elem.price)
                    db.session.add(item)
                item = Order_items(order_id=my_order.id, item="Доставка", count=1,
                                   about='Доставка заказа по указанному адресу.', price=int(request.form['d_cost']))
                db.session.add(item)
                db.session.commit()
                try:
                    send_email(my_order.name, my_order.id, my_order.email, 'успешно принят и уже готовится')
                    return redirect('/my_orders')
                except Exception:
                    return render_template('error.html', error='указан неверный email')
        else:
            return render_template("ordering.html", summa=summa, form=form, title='Оформление заказа · Pizza Online')


    @app.route('/basket', methods=['GET', 'POST'])
    @login_required
    def basket():
        baskets = Basket.query.all()
        for i in range(1, len(baskets) + 3):
            s = 'btn' + str(i)
            r = request.form.get(s)
            if r == '+':
                my_basket = Basket.query.filter_by(user_id=current_user.id, id=i).first()
                my_basket.count += 1
            elif r == '-':
                my_basket = Basket.query.get(i)
                my_basket.count -= 1
            d = 'del' + str(i)
            r = request.form.get(d)
            if r == 'Удалить':
                my_basket = Basket.query.get(i)
                db.session.delete(my_basket)
        db.session.commit()
        if request.form.get("btn") == "Оформить заказ":
            return redirect('/ordering')
        elif request.form.get("btn") == "Очистить корзину":
            my_basket = Basket.query.all()
            for elem in my_basket:
                db.session.delete(elem)
            db.session.commit()
        items = Basket.query.filter_by(user_id=current_user.id).all()
        update_basket()
        summa = 0
        for elem in items:
            summa += elem.price * int(elem.count)
        return render_template("basket.html", data=items, summa=summa, title='Корзина · Pizza Online')


    def update_basket():
        count = Basket.query.filter_by(user_id=current_user.id).all()
        global basket_count
        basket_count = len(count)
except Exception as e:
    print(e)


if __name__ == '__main__':
    app.debug = True
    app.run()
