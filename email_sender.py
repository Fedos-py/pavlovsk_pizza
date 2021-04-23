import smtplib  # Импортируем библиотеку по работе с SMTP
import os
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


def send_email(name, idi):

    with open(Path("index.html"), encoding='utf-8') as file:
        html = file.read()
    html = html.replace('{{name}}', name)
    html = html.replace('{{id}}', str(idi))
    # Добавляем необходимые подклассы - MIME-типы
    addr_from = "fastfood.p@yandex.ru"  # Адресат
    addr_to = "fedor.n585@gmail.com"  # Получатель
    password = "Yandex2021"  # Пароль
    msg = MIMEMultipart()  # Создаем сообщение
    msg['From'] = addr_from  # Адресат
    msg['To'] = addr_to  # Получатель
    msg['Subject'] = 'Ваш заказ принят!'  # Тема сообщения
    body = "Мы уже начали готовить Ваш заказ :)"
    msg.attach(MIMEText(html, 'html'))  # Добавляем в сообщение текст
    server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)  # Создаем объект SMTP
    server.set_debuglevel(
        True)  # Включаем режим отладки - если отчет не нужен, строку можно закомментировать                                 # Начинаем шифрованный обмен по TLS
    server.login(addr_from, password)  # Получаем доступ
    server.send_message(msg)  # Отправляем сообщение
    server.quit()  # Выходим