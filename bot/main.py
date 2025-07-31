import logging  # Для записи логов (что происходит с ботом)
import gspread  # Для работы с Google Sheets
from google.oauth2.service_account import Credentials  # Для авторизации в Google
from telegram import Update  # Основной класс для работы с Telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes  # Для создания бота

# Настраиваем логирование (запись событий в файл)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат записи: время - имя - уровень - сообщение
    level=logging.INFO  # Уровень важности: INFO (информация), ERROR (ошибки), WARNING (предупреждения)
)
logger = logging.getLogger(__name__)  # Создаем объект для записи логов

# Читаем токен бота из файла
with open("bot/token.txt") as f:
    TOKEN = f.read().strip()

# Настройки для подключения к Google Sheets
with open("bot/spreadsheet.txt") as f:
    SPREADSHEET_ID = f.read().strip() 
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']  # Разрешения для доступа к Google Sheets

# Пытаемся подключиться к Google Sheets
try:
    # Создаем объект для авторизации в Google
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    # Авторизуемся в Google Sheets
    client = gspread.authorize(creds)
    # Открываем таблицу по ID
    googletable = client.open_by_key(SPREADSHEET_ID)
    # Получаем лист "Meetings" из таблицы
    meetings = googletable.worksheet('Meetings')
    logger.info("Подключение к Google Sheets успешно")  # Записываем в лог об успехе
except Exception as e:  # Если произошла ошибка
    logger.error(f"Ошибка подключения к Google Sheets: {e}")  # Записываем ошибку в лог
    meetings = None  # Устанавливаем meetings в None (пустое значение)

# Словарь для хранения состояния пользователей (как память бота)
# Ключ - ID пользователя, значение - информация о том, что он делает
user_states = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие и показ доступных команд"""
    user_id = update.effective_user.id  # Получаем ID пользователя
    logger.info(f"Получена команда /start от пользователя {user_id}")  # Записываем в лог
    
    # Отправляем приветственное сообщение с списком команд
    await update.message.reply_text(
        "👋 Привет! Я бот для создания встреч.\n\n"
        "Доступные команды:\n"
        "/create - Создать новую встречу\n"
        "/list - Показать все встречи\n"
        "/help - Показать справку\n"
        "/cancel - Отменить создание встречи"
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - показывает подробную справку"""
    await update.message.reply_text(
        "📚 Справка по командам:\n\n"
        "/start - Начать работу с ботом\n"
        "/create - Создать новую встречу\n"
        "/list - Показать все встречи\n"
        "/help - Показать эту справку\n"
        "/cancel - Отменить создание встречи\n\n"
        "💡 Для создания встречи используйте команду /create"
    )

# /create
async def create_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /create - начинает процесс создания встречи"""
    user_id = update.effective_user.id  # Получаем ID пользователя
    logger.info(f"Пользователь {user_id} начал создание встречи")  # Записываем в лог
    
    # Создаем запись в памяти бота для этого пользователя
    user_states[user_id] = {
        "step": "title",  # Текущий шаг - ввод названия
        "title": None,  # Название встречи (пока пустое)
        "description": None,  # Описание встречи (пока пустое)
        "datetime": None  # Дата и время (пока пустое)
    }
    
    # Просим пользователя ввести название встречи
    await update.message.reply_text(
        "📝 Создание новой встречи\n\n"
        "Введите название встречи:"
    )

# /cancel
async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cancel - отменяет создание встречи"""
    user_id = update.effective_user.id  # Получаем ID пользователя
    
    if user_id in user_states:  # Если пользователь в процессе создания встречи
        del user_states[user_id]  # Удаляем его из памяти бота
        await update.message.reply_text("❌ Создание встречи отменено.")
        logger.info(f"Пользователь {user_id} отменил создание встречи")  # Записываем в лог
    else:  # Если пользователь не создает встречу
        await update.message.reply_text("🤷‍♂️ Нечего отменять. Используйте /create для создания встречи.")

# /list
async def list_meetings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /list - показывает все созданные встречи"""
    try:  # Пытаемся выполнить код
        if meetings:  # Если подключение к Google Sheets успешно
            # Получаем все встречи из таблицы
            all_meetings = meetings.get_all_records()
            
            if not all_meetings:  # Если встреч нет
                await update.message.reply_text("📋 Пока что нет созданных встреч.\n\n💡 Используйте /create для создания первой встречи!")
                return  # Выходим из функции
            
            # Формируем текст со списком встреч
            meetings_text = "📋 Список всех встреч:\n\n"
            
            # Проходим по каждой встрече
            for meeting in all_meetings:
                # Выбираем эмодзи в зависимости от статуса
                status_emoji = "✅" if meeting.get('status') == 'active' else "❌"
                # Добавляем информацию о встрече в текст
                meetings_text += f"{status_emoji} **{meeting.get('title', 'Без названия')}**\n"
                meetings_text += f"📅 {meeting.get('datetime', 'Дата не указана')}\n"
                if meeting.get('description'):  # Если есть описание
                    meetings_text += f"📝 {meeting.get('description')}\n"
                meetings_text += f"🆔 ID: {meeting.get('meeting_id', 'N/A')}\n\n"
            
            # Отправляем список встреч пользователю
            await update.message.reply_text(meetings_text)
            logger.info(f"Показан список встреч: {len(all_meetings)} встреч")  # Записываем в лог
        else:  # Если не удалось подключиться к Google Sheets
            await update.message.reply_text("⚠️ Не удалось подключиться к базе данных.\n\n💡 Используйте /create для создания встречи!")
            
    except Exception as e:  # Если произошла ошибка
        logger.error(f"❌ Ошибка при получении списка встреч: {e}")  # Записываем ошибку в лог
        await update.message.reply_text("❌ Ошибка при получении списка встреч.\n\n💡 Используйте /create для создания встречи!")

# Обработка обычных текстовых сообщений (не команд)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений от пользователей"""
    user_id = update.effective_user.id  # Получаем ID пользователя
    message_text = update.message.text  # Получаем текст сообщения
    
    logger.info(f"Получено сообщение: '{message_text}' от пользователя {user_id}")  # Записываем в лог
    
    # Проверяем, есть ли пользователь в процессе создания встречи
    if user_id in user_states:  # Если пользователь создает встречу
        await handle_meeting_creation(update, context)  # Вызываем функцию создания встречи
    else:  # Если пользователь не создает встречу
        await update.message.reply_text(
            "💡 Используйте команду /create для создания встречи\n"
            "Или /help для справки"
        )

# Пошаговое создание встречи
async def handle_meeting_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пошаговое создание встречи - обрабатывает каждый шаг"""
    user_id = update.effective_user.id  # Получаем ID пользователя
    message_text = update.message.text  # Получаем текст сообщения
    state = user_states[user_id]  # Получаем состояние пользователя из памяти
    
    if state["step"] == "title":  # Если пользователь вводит название
        # Сохраняем название встречи
        state["title"] = message_text
        state["step"] = "description"  # Переходим к следующему шагу
        
        # Просим ввести описание
        await update.message.reply_text(
            "📝 Введите описание встречи (или напишите 'нет' для пропуска):"
        )
        logger.info(f"Пользователь {user_id} ввел название: {message_text}")  # Записываем в лог
        
    elif state["step"] == "description":  # Если пользователь вводит описание
        # Сохраняем описание встречи
        if message_text.lower() != 'нет':  # Если пользователь не написал "нет"
            state["description"] = message_text
        else:  # Если пользователь написал "нет"
            state["description"] = ""
        state["step"] = "datetime"  # Переходим к следующему шагу
        
        # Просим ввести дату и время
        await update.message.reply_text(
            "📅 Введите дату и время встречи в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2024 14:30"
        )
        logger.info(f"Пользователь {user_id} ввел описание: {message_text}")  # Записываем в лог
        
    elif state["step"] == "datetime":  # Если пользователь вводит дату и время
        # Сохраняем дату и время
        state["datetime"] = message_text
        state["step"] = "confirm"  # Переходим к подтверждению
        
        # Показываем итоговую информацию для проверки
        await update.message.reply_text(
            f"📋 Проверьте информацию о встрече:\n\n"
            f"🎯 Название: {state['title']}\n"
            f"📝 Описание: {state['description'] or 'Не указано'}\n"
            f"📅 Дата и время: {state['datetime']}\n\n"
            f"Все верно? Напишите 'да' для создания или 'нет' для отмены."
        )
        logger.info(f"Пользователь {user_id} ввел дату: {message_text}")  # Записываем в лог
        
    elif state["step"] == "confirm":  # Если пользователь подтверждает создание
        if message_text.lower() == 'да':  # Если пользователь написал "да"
            # Создаем встречу и сохраняем в Google Sheets
            try:  # Пытаемся сохранить
                if meetings:  # Если подключение к Google Sheets успешно
                    # Получаем количество существующих встреч для создания ID
                    existing_meetings = meetings.get_all_records()
                    meeting_id = len(existing_meetings) + 1  # Новый ID = количество существующих + 1
                    
                    # Подготавливаем данные для сохранения в таблицу
                    meeting_data = [
                        meeting_id,  # meeting_id - номер встречи
                        state['title'],  # title - название встречи
                        state['description'] or '',  # description - описание (или пустая строка)
                        state['datetime'],  # datetime - дата и время
                        '',  # chat_ids - ID чатов (пока пусто)
                        '',  # reminders - напоминания (пока пусто)
                        'active'  # status - статус встречи (активная)
                    ]
                    
                    # Сохраняем данные в Google Sheets
                    meetings.append_row(meeting_data)
                    
                    logger.info(f"✅ Встреча сохранена в Google Sheets: {state['title']}")  # Записываем в лог
                    
                    # Отправляем сообщение об успешном создании
                    await update.message.reply_text(
                        f"✅ Встреча '{state['title']}' успешно создана и сохранена!\n\n"
                        f"📅 Дата: {state['datetime']}\n"
                        f"📝 Описание: {state['description'] or 'Не указано'}\n"
                        f"🆔 ID встречи: {meeting_id}\n\n"
                        f"💡 Используйте /create для создания новой встречи"
                    )
                else:  # Если Google Sheets недоступен
                    # Просто выводим в лог без сохранения
                    logger.info(f"Создана встреча (без сохранения): {state}")
                    
                    await update.message.reply_text(
                        f"✅ Встреча '{state['title']}' успешно создана!\n\n"
                        f"📅 Дата: {state['datetime']}\n"
                        f"📝 Описание: {state['description'] or 'Не указано'}\n\n"
                        f"⚠️ Данные не сохранены (ошибка подключения к Google Sheets)\n\n"
                        f"💡 Используйте /create для создания новой встречи"
                    )
                    
            except Exception as e:  # Если произошла ошибка при сохранении
                logger.error(f"❌ Ошибка при сохранении встречи: {e}")  # Записываем ошибку в лог
                await update.message.reply_text(
                    f"✅ Встреча '{state['title']}' создана!\n\n"
                    f"📅 Дата: {state['datetime']}\n"
                    f"📝 Описание: {state['description'] or 'Не указано'}\n\n"
                    f"⚠️ Ошибка при сохранении в базу данных\n\n"
                    f"💡 Используйте /create для создания новой встречи"
                )
            
            # Очищаем состояние пользователя (забываем, что он создавал встречу)
            del user_states[user_id]
            
        else:  # Если пользователь написал что-то кроме "да"
            await update.message.reply_text(
                "❌ Создание встречи отменено.\n"
                "💡 Используйте /create для создания новой встречи"
            )
            # Очищаем состояние пользователя
            del user_states[user_id]

# Главная функция - точка входа в программу
def main():
    """Запускаем бота - основная функция"""
    logger.info("Запускаем бота с командами...")  # Записываем в лог о запуске
    
    # Создаем приложение Telegram бота
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд (что делать при каждой команде)
    application.add_handler(CommandHandler("start", start)) 
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("create", create_meeting))
    application.add_handler(CommandHandler("list", list_meetings))
    application.add_handler(CommandHandler("cancel", cancel_creation))
    
    # Добавляем обработчик текстовых сообщений (не команд)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    print("🤖 Бот с командами запущен!")  # Выводим сообщение в консоль
    logger.info("Бот запущен и готов к работе")  # Записываем в лог
    application.run_polling()  # Запускаем бота в режиме polling (постоянно проверяем новые сообщения)

if __name__ == '__main__':
    main()