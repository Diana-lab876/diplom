import telebot
from telebot import types
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres"
)
cursor = conn.cursor()

bot = telebot.TeleBot('6607822302:AAFg8S7xCmHV1npfe_A9dtoSTr5-xBh_TIQ')

@bot.message_handler(commands=['start'])
def start(message):
    user_name = message.from_user.username
    cursor.execute("""SELECT COUNT(*) FROM teacher WHERE nickname = %s""", (user_name,))
    count = cursor.fetchone()[0]
    if count > 0:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        add_student_button = types.KeyboardButton("Добавить студента")
        view_homework_button = types.KeyboardButton("Посмотреть дз")
        view_analytics_button = types.KeyboardButton("Посмотреть аналитику")
        view_class_list_button = types.KeyboardButton("Посмотреть список класса")
        view_class_rating_button = types.KeyboardButton("Рейтинг класса")
        view_other_classes_rating_button = types.KeyboardButton("Рейтинг среди других классов")
        give_homework_button = types.KeyboardButton("Выдать домашнее задание")
        markup.add(add_student_button, view_homework_button, view_analytics_button, view_class_list_button, view_class_rating_button, view_other_classes_rating_button, give_homework_button)
        bot.send_message(message.from_user.id, 'Вы уже зарегистрированы.', reply_markup=markup)
    else:
        bot.send_message(message.from_user.id, "Добрый день! Напишите свое ФИО?")
        bot.register_next_step_handler(message, get_name)

def get_name(message):
    global name
    global surname
    global patronymic
    surname, name, patronymic = message.text.split()[:3]
    user_name = message.from_user.username
    cursor.execute("""INSERT INTO teacher (name, surname, patronymic, nickname) VALUES (%s, %s, %s, %s)""",
                   (name, surname, patronymic, user_name))
    conn.commit()
    bot.send_message(message.from_user.id, "Вы успешно зарегистрированы!")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    add_student_button = types.KeyboardButton("Добавить студента")
    view_homework_button = types.KeyboardButton("Посмотреть дз")
    view_analytics_button = types.KeyboardButton("Посмотреть аналитику")
    view_class_list_button = types.KeyboardButton("Посмотреть список класса")
    view_class_rating_button = types.KeyboardButton("Рейтинг класса")
    view_other_classes_rating_button = types.KeyboardButton("Рейтинг среди других классов")
    give_homework_button = types.KeyboardButton("Выдать домашнее задание")
    markup.add(add_student_button, view_homework_button, view_analytics_button, view_class_list_button, view_class_rating_button, view_other_classes_rating_button, give_homework_button)
    bot.send_message(message.from_user.id, 'Теперь вы можете добавить студента, посмотреть дз или аналитику.', reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.text == "Добавить студента":
        bot.send_message(message.from_user.id, "Введите фамилию и имя студента:")
        bot.register_next_step_handler(message, get_student_name)
    elif message.text == "Посмотреть список класса":
        view_class_list(message)
    elif message.text == "Рейтинг класса":
        view_class_rating(message)
    elif message.text == "Рейтинг среди других классов":
        view_other_classes_rating(message)
    elif message.text == "Посмотреть дз":
        view_homework(message)
    elif message.text == "Посмотреть аналитику":
        view_analytics(message)
    elif message.text == "Выдать домашнее задание":
        bot.send_message(message.from_user.id, "Пожалуйста, введите номер и тему домашнего задания в формате 'номер тема'.")
        bot.register_next_step_handler(message, get_homework_number_and_topic)
    else:
        bot.send_message(message.from_user.id, 'Напиши /start')

def get_student_name(message):
    global student_surname
    global student_name
    student_surname, student_name = message.text.split()[:2]
    user_name = message.from_user.username  # Получаем имя пользователя
    cursor.execute("""SELECT id FROM teacher WHERE nickname = %s""", (user_name,))
    teacher_id = cursor.fetchone()[0]

    cursor.execute("""SELECT id FROM student WHERE surname = %s AND name = %s""", (student_surname, student_name))
    student = cursor.fetchone()
    if student:
        student_id = student[0]
        cursor.execute("""UPDATE student SET teacher__id = %s WHERE id = %s""", (teacher_id, student_id))
        conn.commit()
        bot.send_message(message.from_user.id, "Студент добавлен.")
    else:
        bot.send_message(message.from_user.id, "Студент с таким именем и фамилией не найден.")

def view_homework(message):
    user_name = message.from_user.username
    cursor.execute("""SELECT id FROM teacher WHERE nickname = %s""", (user_name,))
    teacher_id = cursor.fetchone()[0]

    cursor.execute("""SELECT id, text_dz, error FROM homework 
                      WHERE student_id IN (SELECT id FROM student WHERE teacher__id = %s) 
                      AND used = FALSE""", (teacher_id,))
    homeworks = cursor.fetchall()

    if homeworks:
        for hw in homeworks:
            homework_id, text_dz, error = hw
            bot.send_message(message.from_user.id, f"Домашнее задание: {text_dz}\nОшибка: {error}")

            markup = types.InlineKeyboardMarkup(row_width=4)
            buttons = [types.InlineKeyboardButton(str(i), callback_data=f"grade_{homework_id}_{i}") for i in range(1, 13)]
            markup.add(*buttons)
            bot.send_message(message.from_user.id, "Поставьте оценку:", reply_markup=markup)
    else:
        bot.send_message(message.from_user.id, "Нет домашних заданий для проверки.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("grade_"))
def callback_grade(call):
    _, homework_id, grade = call.data.split("_")
    homework_id = int(homework_id)
    grade = int(grade)

    cursor.execute("""UPDATE homework SET markdown = %s, used = TRUE WHERE id = %s""", (grade, homework_id))
    conn.commit()

    bot.send_message(call.message.chat.id, f"Оценка {grade} выставлена за дз.")

def view_analytics(message):
    user_name = message.from_user.username
    cursor.execute("""SELECT id FROM teacher WHERE nickname = %s""", (user_name,))
    teacher_id = cursor.fetchone()[0]

    # Количество студентов
    cursor.execute("""SELECT COUNT(*) FROM student WHERE teacher__id = %s""", (teacher_id,))
    student_count = cursor.fetchone()[0]

    # Средний балл
    cursor.execute("""SELECT AVG(markdown) FROM homework 
                          WHERE student_id IN (SELECT id FROM student WHERE teacher__id = %s) 
                          AND markdown IS NOT NULL""", (teacher_id,))
    average_grade = cursor.fetchone()[0] or 0  # Если нет оценок, установить в 0

    # Количество непроверенных домашних заданий
    cursor.execute("""SELECT COUNT(*) FROM homework 
                          WHERE student_id IN (SELECT id FROM student WHERE teacher__id = %s) 
                          AND used = FALSE""", (teacher_id,))
    ungraded_homework_count = cursor.fetchone()[0]

    # Количество сданных заданий по каждому number_dz
    cursor.execute("""SELECT number_dz, COUNT(*) FROM homework 
                          WHERE student_id IN (SELECT id FROM student WHERE teacher__id = %s) 
                          GROUP BY number_dz""", (teacher_id,))
    homework_counts = cursor.fetchall()

    analytics_message = (f"*Класс номер:* {teacher_id}\n"
                         f"*Количество студентов:* {student_count}\n"
                         f"*Средний балл:* {average_grade:.2f}\n"
                         f"*Количество непроверенных домашних заданий:* {ungraded_homework_count}\n"
                         f"*Количество сданных заданий по каждому номеру дз:*\n")

    for number_dz, count in homework_counts:
        analytics_message += f"ДЗ {number_dz}: {count}\n"

    bot.send_message(message.from_user.id, analytics_message, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    if call.data == "yes":
        bot.send_message(call.message.chat.id, 'Запомню : )')
    elif call.data == "no":
        bot.send_message(call.message.chat.id, 'Напомни : )')

# Functionality for Class List
def view_class_list(message):
    user_name = message.from_user.username
    cursor.execute("""SELECT surname, name FROM student WHERE teacher__id = (SELECT id FROM teacher WHERE nickname = %s) ORDER BY surname, name""", (user_name,))
    class_list = cursor.fetchall()
    if class_list:
        class_list_str = "\n".join([f"{i+1}. {row[0]} {row[1]}" for i, row in enumerate(class_list)])
        bot.send_message(message.from_user.id, f"Список класса:\n{class_list_str}")
    else:
        bot.send_message(message.from_user.id, "Класс пуст.")

def view_class_rating(message):
    user_name = message.from_user.username
    cursor.execute("""SELECT s.surname, s.name, COALESCE(AVG(h.markdown), 0) 
                      FROM student s
                      LEFT JOIN homework h ON s.id = h.student_id 
                      WHERE s.teacher__id = (SELECT id FROM teacher WHERE nickname = %s) 
                      GROUP BY s.surname, s.name
                      ORDER BY AVG(h.markdown) ASC""", (user_name,))
    class_ratings = cursor.fetchall()
    class_number = 1
    if class_ratings:
        class_rating_str = ""
        for i, row in enumerate(class_ratings):
            class_rating_str += f"{class_number}. {row[0]} {row[1]} - {row[2]:.2f}\n"
            class_number += 1
        bot.send_message(message.from_user.id, f"Рейтинг вашего класса:\n{class_rating_str}")
    else:
        bot.send_message(message.chat.id, "Рейтинг вашего класса пока не доступен.")

def view_other_classes_rating(message):
    user_name = message.from_user.username
    cursor.execute("""SELECT t.id, COALESCE(AVG(h.markdown), 0)
                      FROM teacher t
                      JOIN student s ON t.id = s.teacher__id
                      LEFT JOIN homework h ON s.id = h.student_id 
                      WHERE t.id != (SELECT id FROM teacher WHERE nickname = %s) 
                      GROUP BY t.id
                      ORDER BY AVG(h.markdown) DESC""", (user_name,))
    other_classes_ratings = cursor.fetchall()
    if other_classes_ratings:
        other_classes_rating_str = "\n".join([f"Класс {row[0]} - {row[1]:.2f}" for row in other_classes_ratings])
        bot.send_message(message.from_user.id, f"Рейтинг среди других классов:\n{other_classes_rating_str}")
    else:
        bot.send_message(message.from_user.id, "Рейтинг среди других классов пока не доступен.")

def get_homework_number_and_topic(message):
    global number_dz, topic
    number_dz, topic = message.text.split(maxsplit=1)
    user_name = message.from_user.username
    cursor.execute("""SELECT id FROM teacher WHERE nickname = %s""", (user_name,))
    teacher_id = cursor.fetchone()[0]

    cursor.execute("""SELECT COUNT(*) FROM exercise WHERE teacher_id = %s AND number = %s""", (teacher_id, number_dz))
    if cursor.fetchone()[0] > 0:
        bot.send_message(message.from_user.id, "ДЗ с таким номером уже выдано. Пожалуйста, введите другой номер.")
        bot.register_next_step_handler(message, get_homework_number_and_topic)
    else:
        bot.send_message(message.from_user.id, "Пожалуйста, введите ссылку на Google Doc с домашним заданием.")
        bot.register_next_step_handler(message, get_homework_link)

def get_homework_link(message):
    global link
    link = message.text
    bot.send_message(message.from_user.id, "Пожалуйста, введите ссылку на статью для выполнения домашнего задания.")
    bot.register_next_step_handler(message, get_article_link)

def get_article_link(message):
    global article_link
    article_link = message.text
    bot.send_message(message.from_user.id, "Пожалуйста, введите правильный ответ на дз.")
    bot.register_next_step_handler(message, get_homework_answer)

def get_homework_answer(message):
    answer = message.text
    user_name = message.from_user.username
    cursor.execute("""SELECT id FROM teacher WHERE nickname = %s""", (user_name,))
    teacher_id = cursor.fetchone()[0]
    cursor.execute("""INSERT INTO exercise (teacher_id, number, topic, exercise, article_link, answer) VALUES (%s, %s, %s, %s, %s, %s)""", (teacher_id, number_dz, topic, link, article_link, answer))
    conn.commit()
    bot.send_message(message.from_user.id, "Домашнее задание успешно выдано.")

bot.polling(none_stop=True, interval=0)
