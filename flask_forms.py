from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

    def __repr__(self):
        return '<User %r>' % self.username

class AddItemForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    price = StringField('Цена', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Добавить')

    def __repr__(self):
        return '<User %r>' % self.username