import telebot
import os
import subprocess

# Замените 'YOUR_TOKEN' на ваш токен бота
TOKEN = '7117986911:AAGLCRk1sjZCs_FuaVNET5PZTdmJb_G60lo'

bot = telebot.TeleBot(TOKEN)
# Папка, содержащая PDF файлы (путь относительно текущей директории проекта)
PDF_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'test_diplom')

# Функция для обработки сообщения с ошибкой
def handle_error(message, error_message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=3)
    for i in range(1, 13):
        markup.add(telebot.types.KeyboardButton(str(i)))
    bot.send_message(message.chat.id, error_message, reply_markup=markup)

# Обработчик команды /start и /help
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Пришли мне свой код для проверки.")

# Обработчик прикрепленных документов
@bot.message_handler(content_types=['document'])
def handle_document(message):
    # Проверяем, является ли прикрепленный файл Python-скриптом (.py)
    if message.document.file_name.endswith('.py'):
        try:
            # Получаем информацию о файле
            file_info = bot.get_file(message.document.file_id)
            file_path = os.path.join('downloads', message.document.file_name)

            # Загружаем файл на сервер
            downloaded_file = bot.download_file(file_info.file_path)
            with open(file_path, 'wb') as new_file:
                new_file.write(downloaded_file)

            # Проверяем код в файле
            try:
                subprocess.check_output(['python', '-m', 'py_compile', file_path], stderr=subprocess.STDOUT)

                # Проверяем код на основе заданных тестов
                with open(file_path, 'r', encoding='utf-8') as file:
                    user_code = file.read()
                    exec(compile(user_code, file_path, 'exec'))
            except subprocess.CalledProcessError as e:
                error_message = f"Ошибка синтаксиса в файле {message.document.file_name}: {e.output.decode()}"
                handle_error(message, error_message)
                return
            except Exception as e:
                error_message = f"Ошибка выполнения кода в файле {message.document.file_name}: {e}"
                handle_error(message, error_message)
                return
            finally:
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_content = file.read()
                bot.reply_to(message, f"Содержимое файла {message.document.file_name}:\n{file_content}")

                # Отправляем соответствующий PDF файл
                pdf_file_name = f"{os.path.splitext(message.document.file_name)[0]}.pdf"
                pdf_file_path = os.path.join(PDF_FOLDER, pdf_file_name)
                if os.path.exists(pdf_file_path):
                    with open(pdf_file_path, 'rb') as pdf_file:
                        bot.send_document(message.chat.id, pdf_file)
                else:
                    bot.reply_to(message, f"PDF файл {pdf_file_name} не найден")

                os.remove(file_path)  # Удаляем временный файл
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка при обработке файла: {e}")
    else:
        bot.reply_to(message, "Пожалуйста, пришлите файл Python-скрипта (.py)")

bot.polling()