import asyncio
import gspread
import logging
import hashlib
import rollbar
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

gc = gspread.service_account(filename='YOUR GOOGLE CLOUD API JSON KEY')
sh = gc.open("TestSurveyTeachers")
worksheet = sh.get_worksheet(0)

TOKEN="YOUR BOT TOKEN"

date = datetime.now().isoformat()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

rollbar.init(
  access_token='d80d85533435451d8a528b2dfd2ef5cd',
  environment='testenv',
  code_version='1.0'
)
rollbar.report_message('Looks like the app has started. Rollbar is running correctly and will only monitor errors & exceptions', 'info')

def TeachersNames(column) -> list:
    logger.info("TeacherNames function called")
    
    worksheet = sh.worksheet("Учителя")

    teacher_names = worksheet.col_values(column)

    logger.info("TeacherNames function output: %s", teacher_names)
    return teacher_names
    

async def MainStart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("MainStart function called")

    query = update.callback_query
    if query:
        await query.answer()

    keyboard = [
        [InlineKeyboardButton("Начать анкету", callback_data="start")],
        [InlineKeyboardButton("Оставить отзыв", callback_data="feedback")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)

    try:
        if query and query.data in ["FeedbackCancel", "FeedbackBack", "BackToStart", "SurveyEnd"]:
            if query.message:
                message = await query.message.reply_text("Привет! Выбери нужную опцию:", reply_markup=reply_markup)
            else:
                logger.error("Query message is None")
        elif update.message:
            message = await update.message.reply_text("Привет! Выбери нужную опцию:", reply_markup=reply_markup)
        else:
            logger.error("Update message is None")
            return
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

async def SurveyClassSelect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyClassSelect function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("8", callback_data="CL:8")],
        [InlineKeyboardButton("9", callback_data="CL:9")],
        [InlineKeyboardButton("10", callback_data="CL:10")],
        [InlineKeyboardButton("11", callback_data="CL:11")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)

    try:
        message = await query.message.reply_text("Супер! Теперь выбери свой класс:", reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

async def SurveyClassSelectHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyClassSelectHandler function called, calling SurveyClassSelectSave and SurveyTeacherSelect")

    await SurveyClassSelectSave(update, context)
    await SurveyTeacherSelect(update, context)

async def SurveyClassSelectSave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyClassSelectSave function called")

    query = update.callback_query
    await query.answer()

    column_values = worksheet.col_values(1)
    first_free_row = len(column_values) + 1

    context.user_data['column_values'] = column_values
    context.user_data['first_free_row'] = first_free_row

    user_id = update.callback_query.from_user.id
    hashed_id = hashlib.sha256(str(user_id).encode('utf-8')).hexdigest()
    logger.info("User hashed ID, %s", hashed_id)
    worksheet.update_cell(first_free_row, 1, hashed_id)
    logger.info("Saved hashed User's ID: %s", hashed_id)
    context.user_data['hashed_id'] = hashed_id

    context.user_data['date'] = date
    worksheet.update_cell(first_free_row, 2, date)
    logger.info(f"Saved date at row {first_free_row}, column 2 with value {date}")

    data_parts = query.data.split(":")
    class_number = int(data_parts[1])
    context.user_data['class'] = class_number
    logger.info("Successfully saved user's class into context data: %s", class_number)
    worksheet.update_cell(first_free_row, 3, class_number)
    logger.info(f"Saved user's class into the sheet at row {first_free_row}, column 3 with value {class_number}")

    context.user_data['row_number'] = first_free_row
    

async def SurveyTeacherSelect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyTeacherSelect function called")

    query = update.callback_query
    await query.answer()

    class_number = context.user_data.get('class')
    column_map = {8: 1, 9: 2, 10: 3, 11: 4}
    column = column_map.get(class_number)

    teacher_names = TeachersNames(column)

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"teacher:{name}")]
        for name in teacher_names
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)

    try:
        message = await query.message.reply_text("Такс, а теперь выбери учителя:", reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()


async def SurveyTeacherSelectHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyTeacherSelectHandler function called")
    
    should_proceed = await SurveyTeacherSelectSave(update, context)
    
    if should_proceed:
        await SurveyQ1(update, context)

async def SurveyTeacherSelectSave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyTeacherSelectSave function called")
    query = update.callback_query
    await query.answer()

    id_column_values = worksheet.col_values(1)
    teacher_column_values = worksheet.col_values(4)
    data_parts = query.data.split(":")
    teacher = data_parts[1]

    first_free_row = context.user_data.get('first_free_row')
    hashed_id = context.user_data.get('hashed_id')

    if hashed_id is None:
        logger.error("hashed_id not found in user_data")
        await query.message.reply_text("Произошла ошибка. Пожалуйста, начните заново.")
        await SurveyTeacherSelect(update, context)
        return

    for existing_hashed_id, existing_teacher in zip(id_column_values, teacher_column_values):
        if existing_hashed_id == hashed_id and existing_teacher == teacher:
            await query.message.reply_text("Ты уже заполнил анкету этого учителя в этом модуле. Выбери другого.")
            await SurveyTeacherSelect(update, context)
            return

    try:
        worksheet.update_cell(first_free_row, 4, teacher)
        logger.info(f"Saved teacher's name at row {first_free_row}, column 4 with value {teacher}")
        return True
    except Exception as e:
        logger.error("Failed to update teacher in worksheet: %s", e)
        rollbar.report_exc_info()
        await query.message.reply_text("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте снова.")

async def SurveyQ1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ1 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q1:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q1:Вариант Б")],
        [InlineKeyboardButton("Вариант В", callback_data="Q1:Вариант В")],
        [InlineKeyboardButton("Вариант Г", callback_data="Q1:Вариант Г")],
        [InlineKeyboardButton("Вариант Д", callback_data="Q1:Вариант Д")],
        [InlineKeyboardButton("Готово!", callback_data="Q1:Submit")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)

    try:
        message = await query.message.reply_text(
        f"Оцени уровень дисциплины на уроке. Можно выбрать несколько вариантов ответа: \n"
        "\n"
        "А) Дисциплина в полном порядке \n"
        "Б) Дисциплина иногда нарушается, но класс быстро успокаивается \n"
        "В) Ученики часто срывают урок \n"
        "Г) Ученики игнорируют любые действия учителя \n"
        "Д) Учитель не реагирует на попытки срыва урока",
        reply_markup=reply_markup
        )
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 1

async def SurveyQ1ButtonHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ1ButtonHandler function called")

    query = update.callback_query
    await query.answer()

    user_selections = context.user_data.get('user_selections_Q1', set())

    if query.data.startswith("Q1:Вариант"):
        data_parts = query.data.split(":")[1]
        option_map = {
            "Вариант А": "Дисциплина в полном порядке",
            "Вариант Б": "Дисциплина иногда нарушается, но класс быстро успокаивается",
            "Вариант В": "Ученики часто срывают урок",
            "Вариант Г": "Ученики игнорируют любые действия учителя",
            "Вариант Д": "Учитель не реагирует на попытки срыва урока",
        }

        option = option_map.get(data_parts, "")

        if option in user_selections:
            user_selections.remove(option)
        else:
            user_selections.add(option)

        context.user_data['user_selections_Q1'] = user_selections

        keyboard = []
        for key, opt in option_map.items():
            if opt in user_selections:
                text = f"{key} ✅"
            else:
                text = f"{key}"

            keyboard.append([InlineKeyboardButton(text, callback_data=f"Q1:{key}")])

        keyboard.append([InlineKeyboardButton("Готово!", callback_data="Q1:Submit")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_reply_markup(reply_markup)

    elif query.data == "Q1:Submit":
        asyncio.create_task(SurveyQ1Save(update, context))
        asyncio.create_task(SurveyQ2(update, context))
    
async def SurveyQ1Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ1Save function called")
    
    query = update.callback_query
    await query.answer()
    
    first_free_row = context.user_data.get("first_free_row")
    option = context.user_data.get('user_selections_Q1', set())
    option_string = ', '.join(option)
    worksheet.update_cell(first_free_row, 5, option_string)
    logger.info(f"Updated Q1 cell at row {first_free_row}, column 5 with value {option}")

async def SurveyQ2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ2 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q2:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q2:Вариант Б")],
        [InlineKeyboardButton("Вариант В", callback_data="Q2:Вариант В")],
        [InlineKeyboardButton("Вариант Г", callback_data="Q2:Вариант Г")],
        [InlineKeyboardButton("Готово!",callback_data="Q2:Submit")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(
            f"Оцени уровень дисциплины на уроке. Можно выбрать несколько вариантов ответа: \n"
            "\n"
            "А) Речь учителя полностью понятна \n"
            "Б) Учитель говорит слишком громко \n"
            "В) Учитель говорит слишком быстро \n"
            "Г) Учитель постоянно делает неуместные паузы, из-за этого теряется мысль", 
            reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 2


async def SurveyQ2ButtonHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ2ButtonHandler function called")

    query = update.callback_query
    await query.answer()

    user_selections = context.user_data.get('user_selections_Q2', set())

    if query.data.startswith("Q2:Вариант"):
        data_parts = query.data.split(":")[1]
        option_map = {
            "Вариант А": "Речь учителя полностью понятна",
            "Вариант Б": "Учитель говорит слишком громко",
            "Вариант В": "Учитель говорит слишком быстро",
            "Вариант Г": "Учитель постоянно делает неуместные паузы, из-за этого теряется мысль",
        }

        option = option_map.get(data_parts, "")

        if option in user_selections:
            user_selections.remove(option)
        else:
            user_selections.add(option)

        context.user_data['user_selections_Q2'] = user_selections

        keyboard = []
        for key, opt in option_map.items():
            if opt in user_selections:
                text = f"{key} ✅"
            else:
                text = f"{key}"

            keyboard.append([InlineKeyboardButton(text, callback_data=f"Q2:{key}")])

        keyboard.append([InlineKeyboardButton("Готово!", callback_data="Q2:Submit")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_reply_markup(reply_markup)

    elif query.data == "Q2:Submit":
        asyncio.create_task(SurveyQ2Save(update, context))
        asyncio.create_task(SurveyQ3(update, context))

async def SurveyQ2Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ2Save function called")
    
    query = update.callback_query
    await query.answer()
    
    first_free_row = context.user_data.get("first_free_row")
    option = context.user_data.get('user_selections_Q2', set())
    option_string = ', '.join(option)
    worksheet.update_cell(first_free_row, 6, option_string)
    logger.info(f"Updated Q2 cell at row {first_free_row}, column 6 with value {option}")

async def SurveyQ3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ3 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q3:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q3:Вариант Б")],
        [InlineKeyboardButton("Вариант В", callback_data="Q3:Вариант В")],
        [InlineKeyboardButton("Вариант Г",callback_data="Q3:Вариант Г")],
        [InlineKeyboardButton("Вариант Д",callback_data="Q3:Вариант Д")],
        [InlineKeyboardButton("Готово!", callback_data="Q3:Submit")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(
            f"Оцени структурированность уроков (понятная последовательность изложения материала). Можно выбрать несколько вариантов ответа: \n"
            "\n"
            "А) Учитель дает материал вразброс, перескакивает с темы на тему \n"
            "Б) Учитель не помогает вести конспект, записи на доске хаотичны и непонятны \n"
            "В) Учитель дает материал последовательно и структурированно \n"
            "Г) Учитель грамотно ведет конспект урока на доске \n"
            "Д) Учитель использует электронные ресурсы для ведения урока (презентации, квизы) \n",
            reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 3

async def SurveyQ3ButtonHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ3ButtonHandler function called")

    query = update.callback_query
    await query.answer()

    user_selections = context.user_data.get('user_selections_Q3', set())

    if query.data.startswith("Q3:Вариант"):
        data_parts = query.data.split(":")[1]
        option_map = {
            "Вариант А": "Учитель дает материал вразброс, перескакивает с темы на тему",
            "Вариант Б": "Учитель не помогает вести конспект, записи на доске хаотичны и непонятны",
            "Вариант В": "Учитель дает материал последовательно и структурированно",
            "Вариант Г": "Учитель грамотно ведет конспект урока на доске",
            "Вариант Д": "Учитель использует электронные ресурсы для ведения урока (презентации, квизы)",
        }

        option = option_map.get(data_parts, "")

        if option in user_selections:
            user_selections.remove(option)
        else:
            user_selections.add(option)

        context.user_data['user_selections_Q3'] = user_selections

        keyboard = []
        for key, opt in option_map.items():
            if opt in user_selections:
                text = f"{key} ✅"
            else:
                text = f"{key}"

            keyboard.append([InlineKeyboardButton(text, callback_data=f"Q3:{key}")])

        keyboard.append([InlineKeyboardButton("Готово!", callback_data="Q3:Submit")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_reply_markup(reply_markup)

    elif query.data == "Q3:Submit":
        asyncio.create_task(SurveyQ3Save(update, context))
        asyncio.create_task(SurveyQ4(update, context))

async def SurveyQ3Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ3Save function called")
    
    query = update.callback_query
    await query.answer()
    
    first_free_row = context.user_data.get("first_free_row")
    option = context.user_data.get('user_selections_Q3', set())
    option_string = ', '.join(option)
    worksheet.update_cell(first_free_row, 7, option_string)
    logger.info(f"Updated Q3 cell at row {first_free_row}, column 7 with value {option}")

async def SurveyQ4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ4 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("5", callback_data="Q4:5")],
        [InlineKeyboardButton("4", callback_data="Q4:4")],
        [InlineKeyboardButton("3", callback_data="Q4:3")],
        [InlineKeyboardButton("2", callback_data="Q4:2")],
        [InlineKeyboardButton("1", callback_data="Q4:1")],
        [InlineKeyboardButton("0", callback_data="Q4:0")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(f"Оцени в баллах загруженность на уроке, где 5 - загруженность превышает твои возможности, а 0 - загруженности недостаточно:", reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 4

async def SurveyQ4Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ4Handler function called")

    asyncio.create_task(SurveyQ4Save(update, context))
    asyncio.create_task(SurveyQ5(update, context))

async def SurveyQ4Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ4Save function called")

    query = update.callback_query
    await query.answer()
    
    first_free_row = context.user_data.get("first_free_row")
    option = query.data.split(":")[1]
    worksheet.update_cell(first_free_row, 8, option)
    logger.info(f"Updated Q4 cell at row {first_free_row}, column 8 with value {option}")

async def SurveyQ5(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ5 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q5:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q5:Вариант Б")],
        [InlineKeyboardButton("Вариант В", callback_data="Q5:Вариант В")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(
            f"Оцени понятность системы оценивания (критерии оценивания известны, ты понимаешь, почему получил такую оценку): \n"
            "\n"
            "А) Система предельно ясная, меня все устраивает \n"
            "Б) Иногда возникают вопросы, но после объяснений учителя все становится понятно \n"
            "В) Я почти ничего не понимаю, мне нужно объяснить критерии оценивания \n",
            reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 5

async def SurveyQ5Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ5Handler function called")

    asyncio.create_task(SurveyQ5Save(update, context))
    asyncio.create_task(SurveyQ6(update, context))

async def SurveyQ5Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ5Save function called")

    query = update.callback_query
    await query.answer()

    data_parts = query.data.split(":")[1]
    option_map = {
            "Вариант А": "Система предельно ясная, меня все устраивает",
            "Вариант Б": "Иногда возникают вопросы, но после объяснений учителя все становится понятно",
            "Вариант В": "Я почти ничего не понимаю, мне нужно объяснить критерии оценивания",
        }

    option = option_map.get(data_parts, "")
    
    first_free_row = context.user_data.get("first_free_row")
    worksheet.update_cell(first_free_row, 9, option)
    logger.info(f"Updated Q5 cell at row {first_free_row}, column 9 with value {option}")

async def SurveyQ6(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ6 function called")

    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q6:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q6:Вариант Б")],
        [InlineKeyboardButton("Вариант В", callback_data="Q6:Вариант В")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(
            f"Оцени скорость проверки работ учителем: \n"
            "\n"
            "А) Учитель быстро проверяет работы и выставляет отметки \n"
            "Б) Учитель часто затягивает с проверкой работ \n"
            "В) Часто приходится напоминать учителю о непроверенных работах \n",
            reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 6

async def SurveyQ6Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ6Handler function called")

    asyncio.create_task(SurveyQ6Save(update, context))
    asyncio.create_task(SurveyQ7(update, context))

async def SurveyQ6Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ6Save function called")

    query = update.callback_query
    await query.answer()

    data_parts = query.data.split(":")[1]
    option_map = {
        "Вариант А": "Учитель быстро проверяет работы и выставляет отметки",
        "Вариант Б": "Учитель часто затягивает с проверкой работ",
        "Вариант В": "Часто приходится напоминать учителю о непроверенных работах",
    }

    option = option_map.get(data_parts, "")
    
    first_free_row = context.user_data.get("first_free_row")
    worksheet.update_cell(first_free_row, 10, option)
    logger.info(f"Updated Q6 cell at row {first_free_row}, column 10 with value {option}")

async def SurveyQ7(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ7 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Да", callback_data="Q7:Да")],
        [InlineKeyboardButton("Скорее да, чем нет", callback_data="Q7:Скорее да, чем нет")],
        [InlineKeyboardButton("Скорее нет, чем да", callback_data="Q7:Скорее нет, чем да")],
        [InlineKeyboardButton("Нет", callback_data="Q7:Нет")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(f"Ты удовлетворен общим количеством и сложностью домашних заданий?", reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 7

async def SurveyQ7Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ7Handler function called")

    asyncio.create_task(SurveyQ7Save(update, context))
    asyncio.create_task(SurveyQ8(update, context))

async def SurveyQ7Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ7Save function called")

    query = update.callback_query
    await query.answer()

    option = query.data.split(":")[1]
    first_free_row = context.user_data.get("first_free_row")
    worksheet.update_cell(first_free_row, 11, option)
    logger.info(f"Updated Q7 cell at row {first_free_row}, column 11 with value {option}")

async def SurveyQ8(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ8 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("От 0 до 30-ти минут", callback_data="Q8:От 0 до 30-ти минут")],
        [InlineKeyboardButton("От 30-ти минут до 60-ти минут", callback_data="Q8:От 30-ти минут до 60-ти минут")],
        [InlineKeyboardButton("Более 60-ти минут", callback_data="Q8:Более 60-ти минут")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(f"Сколько времени ты тратишь на выполнение ДЗ?", reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 8

async def SurveyQ8Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ8Handler function called")

    asyncio.create_task(SurveyQ8Save(update, context))
    asyncio.create_task(SurveyQ9(update, context))

async def SurveyQ8Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ8Save function called")

    query = update.callback_query
    await query.answer()

    option = query.data.split(":")[1]
    first_free_row = context.user_data.get("first_free_row")
    worksheet.update_cell(first_free_row, 12, option)
    logger.info(f"Updated Q8 cell at row {first_free_row}, column 12 with value {option}")

async def SurveyQ9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ9 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q9:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q9:Вариант Б")],
        [InlineKeyboardButton("Вариант В", callback_data="Q9:Вариант В")],
        [InlineKeyboardButton("Вариант Г", callback_data="Q9:Вариант Г")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(
            f"Я понимаю, что домашние задания по этому предмету: \n"
            "\n"
            "А) Мне не нужны, у меня и так все в порядке \n" 
            "Б) Мне нужны, чтобы закрепить правила, прорешать типовые задачи, отработать материал \n"
            "В) Помогают мне лучше понять изучаемый материал, узнать что-то новое \n"
            "Г) Не относятся к изучаемому материалу, не имеют смысла \n",
            reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 9

async def SurveyQ9Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ9Handler function called")

    asyncio.create_task(SurveyQ9Save(update, context))
    asyncio.create_task(SurveyQ10(update, context))

async def SurveyQ9Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ9Save function called")

    query = update.callback_query
    await query.answer()

    data_parts = query.data.split(":")[1]
    option_map = {
        "Вариант А": "Мне не нужны, у меня и так все в порядке",
        "Вариант Б": "Мне нужны, чтобы закрепить правила, прорешать типовые задачи, отработать материал",
        "Вариант В": "Помогают мне лучше понять изучаемый материал, узнать что-то новое",
        "Вариант Г": "Не относятся к изучаемому материалу, не имеют смысла",
    }

    option = option_map.get(data_parts, "")

    first_free_row = context.user_data.get("first_free_row")
    worksheet.update_cell(first_free_row, 13, option)
    logger.info(f"Updated Q9 cell at row {first_free_row}, column 13 with value {option}")

async def SurveyQ10(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ10 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q10:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q10:Вариант Б")],
        [InlineKeyboardButton("Вариант В", callback_data="Q10:Вариант В")],
        [InlineKeyboardButton("Вариант Г", callback_data="Q10:Вариант Г")],
        [InlineKeyboardButton("Вариант Д", callback_data="Q10:Вариант Д")],
        [InlineKeyboardButton("Вариант Е", callback_data="Q10:Вариант Е")],
        [InlineKeyboardButton("Вариант Ж", callback_data="Q10:Вариант Ж")],
        [InlineKeyboardButton("Готово!", callback_data="Q10:Submit")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(
            f"Я хотел бы, чтобы по этому предмету домашние задания были в виде: \n"
            "\n"
            "А) Упражнений на решение типовых задач, отработку правил \n"
            "Б) Коротких роликов и/или подкастов, объясняющих тему \n"
            "В) Небольших фрагментов текста (параграф учебника), объясняющих тему \n"
            "Г) Квизов, игровых упражнений \n"
            "Д) Парных или групповых заданий \n"
            "Е) Творческих заданий \n"
            "Ж) Мне достаточно текущего формата домашних заданий\n"
            "\n"
            "При выборе варианта Ж остальные будут проигнорированы! Если ты выбрал что-то другое, нажми 'Готово!' \n",
            reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 10

async def SurveyQ10ButtonHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ10ButtonHandler function called")

    query = update.callback_query
    await query.answer()

    user_selections = context.user_data.get('user_selections_Q10', set())

    if query.data.startswith("Q10:Вариант"):
        
        if query.data == "Q10:Вариант Ж":
            asyncio.create_task(SurveyQ10Save(update, context))
            asyncio.create_task(SurveyQ11(update, context))

        data_parts = query.data.split(":")[1]
        option_map = {
            "Вариант А": "Упражнений на решение типовых задач, отработку правил",
            "Вариант Б": "Коротких роликов и/или подкастов, объясняющих тему",
            "Вариант В": "Небольших фрагментов текста (параграф учебника), объясняющих тему",
            "Вариант Г": "Квизов, игровых упражнений",
            "Вариант Д": "Парных или групповых заданий",
            "Вариант Е": "Творческих заданий",
            "Вариант Ж": "Мне достаточно текущего формата домашних заданий",
        }

        option = option_map.get(data_parts, "")

        if option in user_selections:
            user_selections.remove(option)
        else:
            user_selections.add(option)

        context.user_data['user_selections_Q10'] = user_selections

        keyboard = []
        for key, opt in option_map.items():
            if opt in user_selections:
                text = f"{key} ✅"
            else:
                text = f"{key}"

            keyboard.append([InlineKeyboardButton(text, callback_data=f"Q10:{key}")])

        keyboard.append([InlineKeyboardButton("Готово!", callback_data="Q10:Submit")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_reply_markup(reply_markup)

    elif query.data == "Q10:Submit":
        asyncio.create_task(SurveyQ10Save(update, context))
        asyncio.create_task(SurveyQ11(update, context))

async def SurveyQ10Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ10Save function called")

    query = update.callback_query
    await query.answer()

    if query.data == "Q10:Вариант Ж":
        option = "Мне достаточно текущего формата домашних заданий"
        first_free_row = context.user_data.get("first_free_row")
        worksheet.update_cell(first_free_row, 14, option)
        logger.info(f"Updated Q10 cell at row {first_free_row}, column 14 with value {option}")
    
    else:
        option = context.user_data.get('user_selections_Q10', set())
        option_string = ', '.join(option)
        first_free_row = context.user_data.get("first_free_row")
        worksheet.update_cell(first_free_row, 14, option_string)
        logger.info(f"Updated Q10 cell at row {first_free_row}, column 14 with value {option}")

async def SurveyQ11(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ11 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Да", callback_data="Q11:Да")],
        [InlineKeyboardButton("Нет", callback_data="Q11:Нет")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(f"Учитель проверяет домашние задания?", reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 11

async def SurveyQ11Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ11Handler function called")

    asyncio.create_task(SurveyQ11Save(update, context))
    asyncio.create_task(SurveyQ12(update, context))

async def SurveyQ11Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ11Save function called")

    query = update.callback_query
    await query.answer()

    option = query.data.split(":")[1]
    first_free_row = context.user_data.get("first_free_row")
    worksheet.update_cell(first_free_row, 15, option)
    logger.info(f"Updated Q11 cell at row {first_free_row}, column 15 with value {option}")

async def SurveyQ12(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ12 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Да", callback_data="Q12:Да")],
        [InlineKeyboardButton("Скорее да, чем нет", callback_data="Q12:Скорее да, чем нет")],
        [InlineKeyboardButton("Скорее нет, чем да", callback_data="Q12:Скорее нет, чем да")],
        [InlineKeyboardButton("Нет", callback_data="Q12:Нет")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(f"Ты удовлетворен качеством получаемой обратной связи?", reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

    context.user_data['survey_step'] = 12

async def SurveyQ12Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ12Handler function called")

    asyncio.create_task(SurveyQ12Save(update, context))
    asyncio.create_task(SurveyQ13(update, context))

async def SurveyQ12Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ12Save function called")

    query = update.callback_query
    await query.answer()

    option = query.data.split(":")[1]
    first_free_row = context.user_data.get("first_free_row")
    worksheet.update_cell(first_free_row, 16, option)
    logger.info(f"Updated Q12 cell at row {first_free_row}, column 16 with value {option}")

async def SurveyQ13(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ13 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q13:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q13:Вариант Б")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(
            f"Оцени степень своего эмоционального спокойствия на уроке: \n"
            "\n"
            "А) Я чаще чувствую себя комфортно и спокойно на уроке \n" 
            "Б) Я чаще чувствую себя НЕкомфортно на уроке \n",
            reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

async def SurveyQ13Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ13Handler function called")

    asyncio.create_task(SurveyQ13Save(update, context))
    asyncio.create_task(SurveyQ14(update, context))

async def SurveyQ13Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ13Save function called")

    query = update.callback_query
    await query.answer()

    option = query.data.split(":")[1]
    first_free_row = context.user_data.get("first_free_row")
    worksheet.update_cell(first_free_row, 17, option)
    logger.info(f"Updated Q13 cell at row {first_free_row}, column 17 with value {option}")

async def SurveyQ14(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q14:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q14:Вариант Б")],
        [InlineKeyboardButton("Вариант В", callback_data="Q14:Вариант В")],
        [InlineKeyboardButton("Вариант Г", callback_data="Q14:Вариант Г")],
        [InlineKeyboardButton("Вариант Д", callback_data="Q14:Вариант Д")],
        [InlineKeyboardButton("Готово!", callback_data="Q14:Submit")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)

    try:
        message = await query.message.reply_text(
            "Оцени отношение учителя к твоим одноклассникам. Можно выбрать несколько вариантов ответа:\n\n"
            "А) Учитель уважает различные мнения одноклассников\n"
            "Б) Учитель одинаково равно уважительно и непредвзято относится ко всем ученикам\n"
            "В) Учитель оперативно реагирует на вопросы одноклассников по теме урока\n"
            "Г) Учитель предвзято относится к некоторым моим одноклассникам\n"
            "Д) Учитель игнорирует некоторых моих одноклассников\n",
            reply_markup=reply_markup
        )
        context.user_data['last_message_id'] = message.message_id
        logger.info(f"Message sent successfully with ID: {message.message_id}")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        rollbar.report_exc_info()

async def SurveyQ14ButtonHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ14ButtonHandler function called")

    query = update.callback_query
    await query.answer()

    user_selections = context.user_data.get('user_selections_Q14', set())

    if query.data.startswith("Q14:Вариант"):

        data_parts = query.data.split(":")[1]
        option_map = {
            "Вариант А": "Учитель уважает различные мнения одноклассников",
            "Вариант Б": "Учитель одинаково равно уважительно и непредвзято относится ко всем ученикам",
            "Вариант В": "Учитель оперативно реагирует на вопросы одноклассников по теме урока",
            "Вариант Г": "Учитель предвзято относится к некоторым моим одноклассникам",
            "Вариант Д": "Учитель игнорирует некоторых моих одноклассников",
        }

        option = option_map.get(data_parts, "")

        if option in user_selections:
            user_selections.remove(option)
        else:
            user_selections.add(option)

        context.user_data['user_selections_Q14'] = user_selections

        keyboard = []
        for key, opt in option_map.items():
            if opt in user_selections:
                text = f"{key} ✅"
            else:
                text = f"{key}"

            keyboard.append([InlineKeyboardButton(text, callback_data=f"Q14:{key}")])

        keyboard.append([InlineKeyboardButton("Готово!", callback_data="Q14:Submit")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_reply_markup(reply_markup)

    elif query.data == "Q14:Submit":
        asyncio.create_task(SurveyQ14Save(update, context))
        asyncio.create_task(SurveyQ15(update, context))

async def SurveyQ14Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ14Save function called")
    
    query = update.callback_query
    await query.answer()
    
    first_free_row = context.user_data.get("first_free_row")
    option = context.user_data.get('user_selections_Q14', set())
    option_string = ', '.join(option)
    worksheet.update_cell(first_free_row, 18, option_string)
    logger.info(f"Updated Q14 cell at row {first_free_row}, column 18 with value {option}")

async def SurveyQ15(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ15 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Вариант А", callback_data="Q15:Вариант А")],
        [InlineKeyboardButton("Вариант Б", callback_data="Q15:Вариант Б")],
        [InlineKeyboardButton("Вариант В", callback_data="Q15:Вариант В")],
        [InlineKeyboardButton("Вариант Г", callback_data="Q15:Вариант Г")],
        [InlineKeyboardButton("Вариант Д", callback_data="Q15:Вариант Д")],
        [InlineKeyboardButton("Готово!", callback_data="Q15:Submit")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message_text = (
            "Оцени отношение учителя к твоим одноклассникам. Можно выбрать несколько вариантов ответа:\n\n"
            "А) Учитель уважает различные мнения одноклассников\n"
            "Б) Учитель одинаково равно уважительно и непредвзято относится ко всем ученикам\n"
            "В) Учитель оперативно реагирует на вопросы одноклассников по теме урока\n"
            "Г) Учитель предвзято относится к некоторым моим одноклассникам\n"
            "Д) Учитель игнорирует некоторых моих одноклассников\n"
        )

        if query and query.message:
            message = await query.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
        elif update.message:
            message = await update.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
        else:
            logger.error("No valid message context found to send the reply.")
            return

        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

async def SurveyQ15ButtonHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ15ButtonHandler function called")

    query = update.callback_query
    await query.answer()

    user_selections = context.user_data.get('user_selections_Q15', set())

    if query.data.startswith("Q15:Вариант"):

        data_parts = query.data.split(":")[1]
        option_map = {
            "Вариант А": "Учитель уважает мое мнение",
            "Вариант Б": "Учитель слышит мои вопросы и отвечает на них",
            "Вариант В": "Учитель демонстрирует непредвзятое отношение ко мне",
            "Вариант Г": "Учитель демонстрирует предвзятое, несправедливое отношение ко мне",
            "Вариант Д": "Учитель игнорирует, не слышит меня",
        }

        option = option_map.get(data_parts, "")

        if option in user_selections:
            user_selections.remove(option)
        else:
            user_selections.add(option)

        context.user_data['user_selections_Q15'] = user_selections

        keyboard = []
        for key, opt in option_map.items():
            if opt in user_selections:
                text = f"{key} ✅"
            else:
                text = f"{key}"

            keyboard.append([InlineKeyboardButton(text, callback_data=f"Q15:{key}")])

        keyboard.append([InlineKeyboardButton("Готово!", callback_data="Q15:Submit")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_reply_markup(reply_markup)

    elif query.data == "Q15:Submit":
        asyncio.create_task(SurveyQ15Save(update, context))
        asyncio.create_task(SurveyQ16(update, context))

async def SurveyQ15Save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ15Save function called")
    
    query = update.callback_query
    await query.answer()
    
    first_free_row = context.user_data.get("first_free_row")
    option = context.user_data.get('user_selections_Q15', set())
    option_string = ', '.join(option)
    worksheet.update_cell(first_free_row, 19, option_string)
    logger.info(f"Updated Q15 cell at row {first_free_row}, column 19 with value {option}")

async def SurveyQ16(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ16 function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Пропустить", callback_data="Q16:Submit")],
    ]

    context.user_data['OQ_column'] = 20

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(f"Возможно, у тебя есть пожелания к работе учителя:", reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()

async def SurveyQ16Handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ16Handler function called")

    query = update.callback_query
    await query.answer()

    context.user_data['OQ_column'] = 20

    if query:
        asyncio.create_task(SurveyEnd(update, context))
    else:
        asyncio.create_task(SurveyOpenQuestionsSave(update, context))

    
async def SurveyEnd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyQ16Save function called")
    
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("В начало", callback_data="SurveyEnd")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)

    try:
        if query :
            message = await query.message.reply_text("Спасибо за заполнение! Можешь вернуться в начало для заполнения другого учителя:", reply_markup=reply_markup)
        elif update.message:
            message = await update.message.reply_text("Спасибо за заполнение! Можешь вернуться в начало для заполнения другого учителя:", reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()


async def SurveyFeedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyFeedback function called")

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="FeedbackCancel")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['OQ_column'] = 21

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        message = await query.message.reply_text(
            f"Здесь ты можешь оставить отзыв об анкете, просто отправь в чат свое сообщение! \n"
            "\n"
            "Небольшая записка: это наш первый опыт использования телеграм-ботов в Пролицее. Все это находится в большом тестировании, и мы будем искренне рады любой обратной связи, предоставленной тобой :) \n",
            reply_markup=reply_markup)
        context.user_data['last_message_id'] = message.message_id
        logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()


async def SurveyOpenQuestionsSave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("SurveyOpenQuestionsSave function called")
    
    query = update.callback_query
    if query:
        await query.answer()

    column = int(context.user_data.get('OQ_column'))
    option = update.message.text
    column_values = worksheet.col_values(1)
    first_free_row = len(column_values) + 1
    worksheet.update_cell(first_free_row, column, option)
    logger.info(f"Updated feedback cell at row {first_free_row}, column {column} with value {option}")

    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="BackToStart")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)  

    try:
        if column == 21:
            if query and query.data:
                message = await query.message.reply_text("Спасибо, мы ценим твою обратную связь! Можешь вернуться обратно:", reply_markup=reply_markup)
            else:
                message = await update.message.reply_text("Спасибо, мы ценим твою обратную связь! Можешь вернуться обратно:", reply_markup=reply_markup)
            context.user_data['last_message_id'] = message.message_id
            logger.info("Message sent successfully with ID: %s", message.message_id)
        elif column == 20:
            if query and query.data:
                message = await query.message.reply_text("Спасибо за заполнение! Мы ценим твою обратную связь! Можешь вернуться в начало:", reply_markup=reply_markup)
            else:
                message = await update.message.reply_text("Спасибо за заполнение! Мы ценим твою обратную связь! Можешь вернуться в начало:", reply_markup=reply_markup)
            context.user_data['last_message_id'] = message.message_id
            logger.info("Message sent successfully with ID: %s", message.message_id)
    except Exception as e:
        logger.error("Failed to send message: %s", e)
        rollbar.report_exc_info()


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", MainStart))
    application.add_handler(CallbackQueryHandler(SurveyClassSelect, pattern="start"))
    application.add_handler(CallbackQueryHandler(SurveyClassSelectHandler, pattern="^CL:"))
    application.add_handler(CallbackQueryHandler(SurveyTeacherSelectHandler, pattern="^teacher:"))
    application.add_handler(CallbackQueryHandler(SurveyQ1ButtonHandler, pattern="^Q1:"))
    application.add_handler(CallbackQueryHandler(SurveyQ2ButtonHandler, pattern="^Q2:"))
    application.add_handler(CallbackQueryHandler(SurveyQ3ButtonHandler, pattern="^Q3:"))
    application.add_handler(CallbackQueryHandler(SurveyQ4Handler, pattern="^Q4:"))
    application.add_handler(CallbackQueryHandler(SurveyQ5Handler, pattern="^Q5:"))
    application.add_handler(CallbackQueryHandler(SurveyQ6Handler, pattern="^Q6:"))
    application.add_handler(CallbackQueryHandler(SurveyQ7Handler, pattern="^Q7:"))
    application.add_handler(CallbackQueryHandler(SurveyQ8Handler, pattern="^Q8:"))
    application.add_handler(CallbackQueryHandler(SurveyQ9Handler, pattern="^Q9:"))
    application.add_handler(CallbackQueryHandler(SurveyQ10ButtonHandler, pattern="^Q10:"))
    application.add_handler(CallbackQueryHandler(SurveyQ11Handler, pattern="^Q11:"))
    application.add_handler(CallbackQueryHandler(SurveyQ12Handler, pattern="^Q12:"))
    application.add_handler(CallbackQueryHandler(SurveyQ13Handler, pattern="^Q13:"))
    application.add_handler(CallbackQueryHandler(SurveyQ14ButtonHandler, pattern="^Q14:"))
    application.add_handler(CallbackQueryHandler(SurveyQ15ButtonHandler, pattern="^Q15:"))
    application.add_handler(CallbackQueryHandler(SurveyQ16Handler, pattern="^Q16:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, SurveyOpenQuestionsSave))
    application.add_handler(CallbackQueryHandler(MainStart, pattern="FeedbackBack"))
    application.add_handler(CallbackQueryHandler(MainStart, pattern="FeedbackCancel"))
    application.add_handler(CallbackQueryHandler(MainStart, pattern="BackToStart"))
    application.add_handler(CallbackQueryHandler(MainStart, pattern="SurveyEnd"))
    application.add_handler(CallbackQueryHandler(SurveyFeedback, pattern="feedback"))

    application.run_polling()

if __name__ == "__main__":
    main()