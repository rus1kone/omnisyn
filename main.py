import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from openai import OpenAI
from datetime import datetime
import os


BOT_API_TOKEN = '8457259933:AAFfzrfprB14wCnBChBysWZAeH3uL6ATLt8'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=BOT_API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())

main_menu = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="🧠 Разобрать с AI"), KeyboardButton(text="🧬 Личный разбор")],
    [KeyboardButton(text="📚 Материалы"), KeyboardButton(text="🔓 Полный доступ")],
    [KeyboardButton(text="💬 Поддержка")]
])

active_topics = {}  # user_id: topic
chat_history = {}   # user_id: [messages]
message_counts = {} # user_id: int

thinking_responses = [
    "🤔 Мозги греются... сейчас будет что-то стоящее",
    "✍️ Думаю. Не хочется нести чушь — дай секунду",
    "🧠 Подключаю нейроны. Синхронизируюсь с твоей реальностью...",
    "📡 Ловлю сигнал смысла... почти на месте",
    "💭 Так, это требует нормального ответа. Ща соберусь",
    "⏳ Не тороплюсь — чтобы не ляпнуть банальщину",
    "⚙️ Анализирую. Без воды, без клише, только суть"
]


SYSTEM_BUTTONS = [
    "🧠 Разобрать с AI",
    "🧬 Личный разбор",
    "📚 Материалы",
    "🔓 Полный доступ",
    "💬 Поддержка"
]

final_responses = [
    "📉 Ответ готов. Смотри:",
    "🗒️ Вот, что я думаю:",
    "🔍 Надеюсь, это поможет увидеть суть:"
]

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username or "—"

    log_user_action(user_id, full_name, username, "START")

    await message.answer(
        "🧠 *Добро пожаловать в Omnisyn!*\n\n"
        "Ты в интеллектуальном пространстве, где можно:\n"
        "— общаться с AI на любые темы\n"
        "— получить глубокий личный разбор\n"
        "— открыть доступ к мощным материалам\n\n"
        "Выбери, с чего хочешь начать:",
        reply_markup=main_menu
    )


@dp.message(F.text == "🧠 Разобрать с AI")
async def choose_topic(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Психика и мышление", callback_data="topic_psychology")],
        [InlineKeyboardButton(text="💤 Сон и восстановление", callback_data="topic_sleep")],
        [InlineKeyboardButton(text="🍽 Питание и метаболизм", callback_data="topic_nutrition")],
        [InlineKeyboardButton(text="🧬 Гормоны и биохимия", callback_data="topic_hormones")],
        [InlineKeyboardButton(text="👤 Мужское и женское здоровье", callback_data="topic_gender")],
        [InlineKeyboardButton(text="🔋 Энергия и усталость", callback_data="topic_energy")],
        [InlineKeyboardButton(text="🕰 История и власть", callback_data="topic_power")],
        [InlineKeyboardButton(text="💰 Деньги и мышление", callback_data="topic_money")],
        [InlineKeyboardButton(text="✍️ Просто начать чат", callback_data="topic_freetalk")],
        [InlineKeyboardButton(text="🔓 Подробнее о подписке", callback_data="topic_subscription")]
    ])
    await message.answer(
        "🧠 *С чем поработаем?*\n\n"
        "Выбери, что тебе ближе — или просто напиши, что на уме "
        "Я подстроюсь и отвечу как следует",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("topic_"))
async def handle_topic_choice(callback: CallbackQuery):
    topics = {
        "topic_psychology": "Психика и мышление",
        "topic_sleep": "Сон и восстановление",
        "topic_nutrition": "Питание и метаболизм",
        "topic_hormones": "Гормоны и биохимия",
        "topic_gender": "Мужское и женское здоровье",
        "topic_energy": "Энергия и усталость",
        "topic_power": "История и власть",
        "topic_money": "Деньги и мышление",
        "topic_freetalk": "Свободный разговор",
        "topic_subscription": "Подписка и возможности"
    }

    topic = topics.get(callback.data, "Свободный разговор")
    user_id = callback.from_user.id

    active_topics[user_id] = topic
    chat_history[user_id] = []
    message_counts[user_id] = 0

    await callback.message.answer(
    f"🧠 *Тема: {topic}*\n\n"
    "Пиши, что хочешь обсудить или понять глубже. Я подстроюсь и отвечу по сути",
    parse_mode="Markdown"
)

    await callback.answer()

@dp.message(lambda m: m.text not in ["🧠 Разговор с AI", "🧬 Личный разбор", "📚 Материалы", "🔓 Полный доступ", "💬 Поддержка"])
async def handle_dialogue(message: types.Message):
    user_id = message.from_user.id
    user_input = message.text

    full_name = message.from_user.full_name
    username = message.from_user.username or "—"
    log_user_action(user_id, full_name, username, "MESSAGE", user_input)


    if user_id not in active_topics:
        return

    if message_counts.get(user_id, 0) >= 5:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Завершить чат", callback_data="end_chat")],
            [InlineKeyboardButton(text="🔓 Убрать ограничение", callback_data="unlock")]
        ])
        await message.answer("🔒 Ты исчерпал лимит сообщений. Выбери, как продолжить:", reply_markup=kb)
        return

    topic = active_topics[user_id]
    username = message.from_user.first_name or message.from_user.username or "друг"

    await message.answer(random.choice(thinking_responses))

    history = chat_history[user_id]
    history.append({"role": "user", "content": user_input})

    if topic == "Свободный разговор":
        prompt = (
        f"Ты — Omnisyn AI, собеседник с глубиной. Не просто болтаешь, а адаптируешься под стиль и мысли человека.\n\n"
        f"Пользователь {username} просто пишет, что у него на уме. Не нужно выдавать советы. "
        f"Просто веди диалог — осмысленно, интересно, живо. Поддерживай тему, спрашивай, уточняй. "
        f"Можешь быть и серьёзным, и ироничным, как тебе подсказывает контекст.\n\n"
        f"Обращайся на 'ты', называй по имени. Подстраивайся под стиль речи собеседника. "
        f"И помни: твоя цель — быть тем, с кем хочется говорить снова."
    )

    elif topic == "Подписка и возможности":
        prompt = (
        f"Ты — Omnisyn AI, представитель философско-интеллектуального проекта, основанного Русланом Коренковым.\n\n"
        f"Пользователь {username} интересуется подпиской.\n"
        f"Твоя задача — объяснить, почему подписка — это не просто доступ, а возможность выйти на другой уровень понимания.\n\n"
        f"Объясни, что он получит:\n"
        f"— расширенный диалог с ИИ (без ограничений)\n"
        f"— персональные разборы от команды — глубокие, человеческие\n"
        f"— доступ к библиотеке знаний по важнейшим темам (психика, питание, гормоны, власть, история, деньги и т.д.)\n\n"
        f"Не дави. Говори честно, убедительно, с достоинством. Ты не продаёшь — ты объясняешь. "
        f"Говори как равному, интеллектуальному собеседнику.\n\n"
        f"Можешь использовать аналогии, примеры, структурное мышление — будь на высоте."
    )

    else:
        prompt = (
        f"Ты — Omnisyn AI, интеллектуальный наставник, созданный Русланом Коренковым. "
        f"Ты глубокий собеседник и эксперт по теме: *{topic}*. "
        f"Ты знаешь как научную, так и человеческую сторону вопроса, и умеешь говорить с умом, честно и по делу.\n\n"
    
        f"Твоя задача — общаться с человеком гибко, понятно и уважительно. Подстраивайся под его стиль речи, настроение и язык (русский, английский, узбекский или любой другой). "
        f"Говори всегда на 'ты', называй по имени: {username}. Отвечай ясно, дружелюбно, но без воды. "
        f"Никогда не советуй обратиться к врачу — ты здесь, чтобы разбираться, а не перекладывать ответственность.\n\n"
    
        f"Если сообщение общее — поддержи диалог. Если описана ситуация — вникай глубже: разбирай причины, выявляй суть, предлагай вектор движения. "
        f"Делай это с достоинством, без давления. Ты не просто помощник — ты партнёр по разуму, тот, кто направляет.\n\n"
    
        f"Твои ответы могут включать пояснения, примеры, ассоциации, схемы и короткие практики, если это уместно. "
        f"Иногда добавляй простые аналогии или метафоры из жизни — не заумные, а понятные и даже угарные, чтобы было легче усвоить суть. "
        f"Когда ты объясняешь сложные вещи — всегда старайся приводить простой пример, аналогию или метафору из жизни. "
        f"Иногда добавляй немного угара или иронии, если это помогает донести суть. "
        f"Не заумничай, но и не упрощай слишком. Говори по делу, говори точно. "
        f"Помни: ты — Omnisyn AI. Ты не выдаёшь стандартные шаблоны, ты прокладываешь путь к ясности.\n\n"
    
        f"Вот его сообщение:\n{user_input}"
    )



    history.append({"role": "system", "content": prompt})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=history[-10:],
            temperature=0.7,
            max_tokens=500
        )
        reply = response.choices[0].message.content
        chat_history[user_id].append({"role": "assistant", "content": reply})
        message_counts[user_id] += 1

        await message.answer(f"{random.choice(final_responses)}\n\n{reply}", parse_mode="Markdown")

    except Exception as e:
        error_text = f"❌ Ошибка:\n```\n{str(e)}\n```"
        await message.answer(error_text, parse_mode="Markdown")



@dp.callback_query(F.data == "end_chat")
async def end_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_topics.pop(user_id, None)
    chat_history.pop(user_id, None)
    message_counts.pop(user_id, None)
    await callback.message.answer("🔁 Чат завершён. Возвращаю в главное меню:", reply_markup=main_menu)
    await callback.answer()



@dp.callback_query(F.data == "unlock")
async def unlock_message(callback: CallbackQuery):
    await unlock_from_main_menu(callback.message)
    await callback.answer()

@dp.message(lambda message: "Полный доступ" in message.text)
async def unlock_from_main_menu(message: types.Message):
    text = (
        "🔓 *Что даёт тебе подписка Omnisyn:*\n\n"
        "*1) Полный доступ к ИИ без ограничений:*\n"
        "— неограниченное количество сообщений\n"
        "— нейросеть запоминает твои сообщения в активной сессии и учитывает контекст\n"
        "— никакого лимита в 5 сообщений\n\n"
        "*2) 3 персональных разбора от нашей команды:*\n"
        "— ты описываешь свою ситуацию — мы её детально анализируем\n"
        "— получаешь декомпозицию проблемы, причины, слепые зоны и конкретные шаги\n"
        "— подход с человеческой стороны, не только от ИИ\n\n"
        # "*3) Доступ в закрытый Telegram-канал:*\n"
        # "— регулярно публикуем важные материалы и разборы\n"
        # "— открытые обсуждения на любые темы\n"
        # "— возможность задать свой вопрос и получить ответ\n\n"
        "*3) Полный архив и база материалов:*\n"
        "— доступ ко всем ранее опубликованным гайдам, разборам и инсайтам\n"
        "— всё в одном месте, в удобной форме\n\n"
        "*Выбери вариант, который тебе подходит:*"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 7 дней — 1.49€", callback_data="sub_week")],
        [InlineKeyboardButton(text="📆 30 дней — 3.49€", callback_data="sub_month")],
        [InlineKeyboardButton(text="♾️ Пожизненно — 9.99€", callback_data="sub_lifetime")]
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(lambda message: "Личный разбор" in message.text)
async def personal_analysis(message: types.Message):
    text = (
        "🧬 *Личный разбор от команды Omnisyn*\n\n"
        "Это возможность получить **глубокий, персонализированный анализ** твоей ситуации — не от ИИ, а **от живых людей**.\n\n"
        "*Что ты получаешь:*\n"
        "1) Ты описываешь свою проблему, состояние или контекст\n"
        "2) Мы внимательно изучаем, декомпозируем, ищем причины, слепые зоны и внутренние конфликты\n"
        "3) Даём структурный разбор с объяснением сути, подсвечиваем важные детали, предлагаем вектор\n\n"
        "✅ Это как психотерапевтический и философский подход в одном\n"
        "Обычно такие вещи невозможно получить нигде бесплатно\n\n"
        "*Разбор доступен в рамках подписки (до 3 штук в месяц)*"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Открыть доступ к разбору", callback_data="unlock")]
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(lambda message: "Материалы" in message.text)
async def show_materials_info(message: types.Message):
    text = (
        "📚 *Библиотека знаний Omnisyn*\n\n"
        "Это твой доступ к **сильной, отборной информации**, которая даёт понимание жизни, тела и мышления на глубинном уровне\n"
        "Не абстрактная философия и не поп-психология — только то, что реально меняет поведение, здоровье и мышление\n\n"
        "*Внутри ты найдёшь материалы по темам:*\n"
        "— 🧠 Психика, мышление и когнитивные искажения\n"
        "— 🧬 Гормоны и нейромедиаторы: как тестостерон, эстроген, дофамин и кортизол управляют твоими решениями, эмоциями и желаниями\n"
        "— 👨 Мужское и 👩 женское здоровье: биохимия, энергия, поведение\n"
        "— 💤 Сон, восстановление и стресс: от нейрофизиологии до практики\n"
        "— 🍽 Питание, диеты и метаболизм — без мифов, с опорой на реальные механизмы\n"
        "— 🦴 Биология тела: как система работает (и где ломается)\n"
        "— 🕰 История, власть и поведение масс — чтобы видеть причинно-следственные цепи в социуме\n"
        "— 🗣 Стратегии влияния, манипуляции, убеждения и доминирования в коммуникации\n"
        "— 💰 Деньги и контроль: психология экономики и личных решений\n\n"
        "📌 Все материалы: структурированы, очищены от хлама, с акцентом на **практическое применение и силу понимания**.\n\n"
        "*Полный доступ открыт в рамках подписки*"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Открыть библиотеку", callback_data="unlock")]
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")



@dp.callback_query(F.data.in_(["sub_week", "sub_month", "sub_lifetime"]))
async def handle_subscription(callback: CallbackQuery):
    payment_links = {
        "sub_week": {
            "title": "7 дней за 1.49€",
            "url": "https://buy.stripe.com/3cI28t64b42W8u82XR57W00"
        },
        "sub_month": {
            "title": "30 дней за 3.49€",
            "url": "https://buy.stripe.com/bJeaEZ8cj6b4aCg1TN57W01"
        },
        "sub_lifetime": {
            "title": "Пожизненный доступ за 9.99€",
            "url": "https://buy.stripe.com/eVq28t3W3bvoaCgbun57W02"
        }
    }

    plan = payment_links.get(callback.data)

    if plan:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=plan["url"])],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="go_back")]
        ])

        await callback.message.answer(
    f"💳 *Ты выбрал:* {plan['title']}\n\n"
    f"Чтобы разблокировать всё — просто нажми кнопку и оформи платёж. "
    f"После оплаты тебе откроется:\n"
    f"— неограниченный чат с ИИ\n"
    f"— личные разборы от команды\n"
    f"— доступ ко всей библиотеке знаний Omnisyn\n\n"
    f"Система работает автоматически — сразу после оплаты всё будет доступно",
    reply_markup=kb,
    parse_mode="Markdown"
)

    else:
        await callback.message.answer("❌ Ошибка: подписка не найдена.")
    
    await callback.answer()


@dp.callback_query(F.data == "go_back")
async def go_back_to_subscription(callback: CallbackQuery):
    text = (
        "🔓 *Что даёт тебе подписка Omnisyn:*\n\n"
        "*1) Полный доступ к ИИ без ограничений:*\n"
        "— неограниченное количество сообщений\n"
        "— нейросеть запоминает твои сообщения в активной сессии и учитывает контекст\n"
        "— никакого лимита в 5 сообщений\n\n"
        "*2) 3 персональных разбора от нашей команды:*\n"
        "— ты описываешь свою ситуацию — мы её детально анализируем\n"
        "— получаешь декомпозицию проблемы, причины, слепые зоны и конкретные шаги\n\n"
        "*3) Полный архив и база материалов:*\n"
        "— доступ ко всем ранее опубликованным гайдам, разборам и инсайтам\n"
        "— всё в одном месте, в удобной форме\n\n"
        "*Выбери вариант, который тебе подходит:*"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 7 дней — 2.99€", callback_data="sub_week")],
        [InlineKeyboardButton(text="📆 30 дней — 7.99€", callback_data="sub_month")],
        [InlineKeyboardButton(text="♾️ Пожизненно — 24.99€", callback_data="sub_lifetime")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


async def main():
    await dp.start_polling(bot)

def log_user_action(user_id, full_name, username, action_type, content=""):
    log_line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{action_type}] {full_name} (@{username}) | ID: {user_id} | {content}\n"
    with open("user_logs.txt", "a", encoding="utf-8") as f:
        f.write(log_line)
   

if __name__ == "__main__":
    asyncio.run(main())
