import psycopg2
import telebot
from telebot import types

conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres"
)
cursor = conn.cursor()

bot = telebot.TeleBot('6834216613:AAEL2h3K6Yw8Rlivga4DMw3iyKjifhzHn_Y')

@bot.message_handler(content_types=['text'])
def start(message):
    if message.text == '/start':
        user_name = message.from_user.username
        cursor.execute("""SELECT COUNT(*) FROM student WHERE nickname = %s""", (user_name,))
        count = cursor.fetchone()[0]
        if count > 0:
            bot.send_message(message.from_user.id, 'Вы уже зарегистрированы.')
        else:
            bot.send_message(message.from_user.id, "Привет! Напиши свое имя и фамилию")
            bot.register_next_step_handler(message, get_name)
    else:
        bot.send_message(message.from_user.id, 'Напиши /start')

def get_name(message):
    global name
    global surname
    name, surname = message.text.split()[:2]
    user_name = message.from_user.username
    cursor.execute("""INSERT INTO student (name, surname, nickname) VALUES (%s, %s, %s)""", (name, surname, user_name))
    conn.commit()
    keyboard = types.InlineKeyboardMarkup()
    key_yes = types.InlineKeyboardButton(text='Да', callback_data='yes')
    keyboard.add(key_yes)
    key_no = types.InlineKeyboardButton(text='Нет', callback_data='no')
    keyboard.add(key_no)
    question = f'Тебя зовут {name} {surname}?'
    bot.send_message(message.from_user.id, text=question, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    if call.data == "yes":
        bot.send_message(call.message.chat.id, 'Запомню : )')
    elif call.data == "no":
        bot.send_message(call.message.chat.id, 'Напомни : )')

bot.polling(none_stop=True, interval=0)
