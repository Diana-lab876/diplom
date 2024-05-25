import telebot
from telebot import types
import psycopg2
import os
import subprocess
import sys
import base64
import requests
import json
import uuid
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter('ignore', InsecureRequestWarning)

conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres"
)
cursor = conn.cursor()

bot = telebot.TeleBot('6834216613:AAEL2h3K6Yw8Rlivga4DMw3iyKjifhzHn_Y')

ERROR_TRANSLATIONS = {
    "Final newline missing": "Отсутствует новая строка в конце файла",
    "Missing module docstring": "Отсутствует строка документации модуля",
    "Module name doesn't conform to snake_case naming style": "Имя модуля не соответствует стилю snake_case",
    "contains a non-ASCII character": "содержит не-ASCII символ",
    "Undefined variable": "Неопределенная переменная",
    "missing-final-newline": "Отсутствует новая строка в конце файла",
    "missing-module-docstring": "Отсутствует строка документации модуля",
    "invalid-name": "Имя модуля не соответствует стилю snake_case",
    "non-ascii-file-name": "Имя файла содержит не-ASCII символ",
    "undefined-variable": "Неопределенная переменная"
}

client_id = '2ada3c9c-e49c-4799-b8f9-3c0932766bf4'
secret = 'e140ff20-0539-4027-b0e9-e2cdcb69a022'
auth = 'MmFkYTNjOWMtZTQ5Yy00Nzk5LWI4ZjktM2MwOTMyNzY2YmY0OmUxNDBmZjIwLTA1MzktNDAyNy1iMGU5LWUyY2RjYjY5YTAyMg=='


def get_giga_token(auth_token, scope='GIGACHAT_API_PERS'):
    rq_uid = str(uuid.uuid4())
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': rq_uid.encode('utf-8'),
        'Authorization': f'Basic {auth_token}'
    }
    payload = {
        'scope': scope
    }
    response = requests.post(url, headers=headers, data=payload, verify=False)
    if response.status_code == 200:
        return response.json()['access_token']
    return None


giga_token = get_giga_token(auth)


def get_chat_completion(auth_token, user_message):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    payload = json.dumps({
        "model": "GigaChat",
        "messages": [
            {
                "role": "user",
                "content": user_message
            }
        ],
        "temperature": 1,
        "top_p": 0.1,
        "n": 1,
        "stream": False,
        "max_tokens": 512,
        "repetition_penalty": 1,
        "update_interval": 0
    })
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {auth_token}'
    }
    response = requests.request("POST", url, headers=headers, data=payload, verify=False)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    return None

@bot.message_handler(commands=['меню'])
def start(message):
    user_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    user_markup.row('Отправить дз', 'Посмотреть рейтинг')
    user_markup.row('Посмотреть оценки за дз', 'Посмотреть выданное дз')
    bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=user_markup)

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    if message.text == 'Отправить дз':
        bot.send_message(message.chat.id, "Пожалуйста, введите номер домашнего задания.")
        bot.register_next_step_handler(message, process_homework)
    elif message.text == 'Посмотреть рейтинг':
        view_class_rating(message)
    elif message.text == 'Посмотреть оценки за дз':
        view_homework_grades(message)
    elif message.text == 'Посмотреть выданное дз':
        view_given_homework(message)
    else:
        bot.send_message(message.chat.id, 'Выберите действие, используя кнопки на клавиатуре.')

def view_class_rating(message):
    user_name = message.from_user.username
    cursor.execute("""SELECT teacher__id FROM student WHERE nickname = %s""", (user_name,))
    teacher_row = cursor.fetchone()
    if teacher_row:
        teacher_id = teacher_row[0]
        cursor.execute("""SELECT surname, name, COALESCE(AVG(h.markdown), 0), nickname 
                          FROM student s
                          LEFT JOIN homework h ON s.id = h.student_id 
                          WHERE s.teacher__id = %s
                          GROUP BY s.surname, s.name, s.nickname
                          ORDER BY AVG(h.markdown) ASC""", (teacher_id,))
        class_ratings = cursor.fetchall()
        if class_ratings:
            class_rating_str = ""
            for i, row in enumerate(class_ratings):
                if row[3] == user_name:
                    class_rating_str += f"**{i + 1}. {row[0]} {row[1]} - {row[2]:.2f}**\n"
                else:
                    class_rating_str += f"{i + 1}. {row[0]} {row[1]} - {row[2]:.2f}\n"
            bot.send_message(message.chat.id, f"Рейтинг вашего класса:\n{class_rating_str}", parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "Рейтинг вашего класса пока не доступен.")
    else:
        bot.send_message(message.chat.id, "Ошибка: Не удалось найти учителя для текущего пользователя.")

def view_homework_grades(message):
    user_name = message.from_user.username
    cursor.execute("""SELECT number_dz, case when markdown is null then 0
                            else markdown end as markdown
                      FROM homework h
                      JOIN student s ON h.student_id = s.id
                      WHERE s.nickname = %s""", (user_name,))
    homework_grades = cursor.fetchall()
    if homework_grades:
        grades_str = "\n".join([f"ДЗ {row[0]} - {'оценка еще не выставлена' if row[1] == 0 else row[1]}" for row in homework_grades])
        bot.send_message(message.chat.id, f"Оценки за домашние задания:\n{grades_str}")
    else:
        bot.send_message(message.chat.id, "У вас пока нет оценок за домашние задания.")

def get_teacher_id(user_name):
    cursor.execute("""SELECT teacher__id FROM student WHERE nickname = %s""", (user_name,))
    teacher_row = cursor.fetchone()
    if teacher_row:
        return teacher_row[0]
    return None

def process_homework(message):
    number_dz = message.text.strip()

    user_name = message.from_user.username
    cursor.execute(
        """SELECT markdown, used FROM homework WHERE number_dz = %s AND student_id = (SELECT id FROM student WHERE nickname = %s)""",
        (number_dz, user_name))
    existing_homework = cursor.fetchone()

    if existing_homework:
        if existing_homework[1]:
            bot.send_message(message.chat.id, f"Это дз уже выполнено и проверено с оценкой {existing_homework[0]}.")
        else:
            bot.send_message(message.chat.id, "Это дз уже отправлено и ожидает проверки.")
        return

    teacher_id = get_teacher_id(user_name)
    cursor.execute("""SELECT COUNT(*) FROM exercise WHERE number = %s AND teacher_id = %s""", (number_dz, teacher_id))
    count = cursor.fetchone()[0]
    if count == 0:
        bot.send_message(message.chat.id, "ДЗ с таким номером не задано вашим учителем.")
        return

    bot.send_message(message.chat.id, 'Пожалуйста, отправьте файл с домашним заданием.')
    bot.register_next_step_handler(message, process_code, number_dz)


def process_code(message, number_dz):
    if not message.document:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте файл с домашним заданием.")
        bot.register_next_step_handler(message, process_code, number_dz)
        return

    file_info = bot.get_file(message.document.file_id)
    file_path = os.path.join('downloads', message.document.file_name)

    downloaded_file = bot.download_file(file_info.file_path)
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    with open(file_path, 'r', encoding='utf-8') as file:
        code = file.read()

    flake8_output = run_flake8(file_path)

    pylint_output = run_pylint(file_path)

    error = None
    try:
        exec(code)
    except Exception as e:
        error = str(e)

    os.remove(file_path)

    user_name = message.from_user.username
    cursor.execute(
        """INSERT INTO homework (student_id, number_dz, text_dz, error, used) VALUES ((SELECT id FROM student WHERE nickname = %s), %s, %s, %s, FALSE)""",
        (user_name, number_dz, code, error))
    conn.commit()

    check_homework_answer(message, number_dz, code, flake8_output, pylint_output, error)


def check_homework_answer(message, number_dz, code, flake8_output, pylint_output, error):
    user_name = message.from_user.username
    teacher_id = get_teacher_id(user_name)

    if teacher_id is None:
        bot.send_message(message.chat.id, 'Ошибка: Не удалось найти учителя для текущего пользователя.')
        return

    cursor.execute("""SELECT answer, article_link FROM exercise WHERE number = %s AND teacher_id = %s""",
                   (number_dz, teacher_id))
    correct_answer_row = cursor.fetchone()

    if correct_answer_row:
        correct_answer, article_link = correct_answer_row
        if correct_answer in code:
            correct_message = "Ваш ответ правильный."
        else:
            correct_message = "Ваш ответ неправильный."

        error_messages = format_error_messages(flake8_output)
        recommendations = ""
        if error_messages:
            recommendations = get_chat_completion(giga_token,
                                                  f"Какие рекомендации вы можете дать для устранения ошибок в Python коде?\n"
                                                  f"{code}\n"
                                                  f"{error_messages}\n"
                                                  f"Пожалуйста, предоставьте ссылки на статьи, которые помогут устранить эти ошибки.")

        result_message = (
            f"{correct_message}\n\n"
            f"Ошибки в стиле:\n{flake8_output}\n\n"
            f"Ошибки в коде:\n{pylint_output}"
        )

        if error:
            result_message += f"\n\nОбнаружена ошибка при выполнении кода:\n{error}"

        if recommendations:
            result_message += f"\n\nРекомендации по устранению ошибок:\n{recommendations}"
        result_message += f"\n\nПрочитайте следующую статью для выполнения домашнего задания: {article_link}"

        bot.send_message(message.chat.id, result_message)
    else:
        bot.send_message(message.chat.id, 'Не найдено правильного ответа для данного задания и учителя.')


def format_error_messages(flake8_output):
    errors = []

    if flake8_output.strip() != "Ошибок не найдено.":
        for line in flake8_output.strip().split('\n'):
            errors.append(line)

    return "\n".join(errors)


def run_flake8(file_path):
    try:
        result = subprocess.run([sys.executable, '-m', 'flake8', '--version'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            return 'Ошибка: flake8 не установлен или недоступен.'

        result = subprocess.run([sys.executable, '-m', 'flake8', file_path], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        return format_flake8_output(result.stdout)
    except Exception as e:
        return str(e)


def format_flake8_output(output):
    if not output.strip():
        return "Ошибок не найдено."

    formatted_output = ""
    for line in output.strip().split('\n'):
        parts = line.split(':')
        if len(parts) >= 4:
            line_number, column_number, error_message = parts[1], parts[2], ':'.join(parts[3:])
            error_message_translated = translate_error_message(error_message.strip())
            formatted_output += f"Строка {line_number}, колонка {column_number}: {error_message_translated}\n"
    return formatted_output


def run_pylint(file_path):
    try:
        result = subprocess.run([sys.executable, '-m', 'pylint', '--version'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            return 'Ошибка: pylint не установлен или недоступен.'

        result = subprocess.run([sys.executable, '-m', 'pylint', file_path], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        return format_pylint_output(result.stdout)
    except Exception as e:
        return str(e)


def format_pylint_output(output):
    if not output.strip():
        return "Ошибок не найдено."

    formatted_output = ""
    for line in output.strip().split('\n'):
        if line.startswith("************* Module"):
            continue
        if line.startswith("---"):
            break
        parts = line.split(':')
        if len(parts) >= 4:
            line_number, column_number, error_message = parts[1], parts[2], ':'.join(parts[3:])
            error_message_translated = translate_error_message(error_message.strip())
            formatted_output += f"Строка {line_number}, колонка {column_number}: {error_message_translated}\n"
        else:
            formatted_output += line + "\n"
    return formatted_output


def translate_error_message(error_message):
    for english, russian in ERROR_TRANSLATIONS.items():
        error_message = error_message.replace(english, russian)
    return error_message


def view_given_homework(message):
    user_name = message.from_user.username
    teacher_id = get_teacher_id(user_name)

    if teacher_id is None:
        bot.send_message(message.chat.id, 'Ошибка: Не удалось найти учителя для текущего пользователя.')
        return

    cursor.execute("""SELECT number, topic, exercise FROM exercise WHERE teacher_id = %s""", (teacher_id,))
    exercises = cursor.fetchall()
    if exercises:
        exercises_str = "\n".join([f"ДЗ {row[0]} - {row[1]}\nСсылка: {row[2]}" for row in exercises])
        bot.send_message(message.chat.id, f"Выданные дз:\n{exercises_str}")
    else:
        bot.send_message(message.chat.id, "Нет выданных дз.")


bot.polling()
