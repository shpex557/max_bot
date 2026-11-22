import asyncio
import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, MessageCreated, Command, MessageCallback, CallbackButton
from maxapi.types.input_media import InputMedia
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

print("1. Скрипт запустился")

TOKEN = "f9LHodD0cOLDRk08UgR5Wro0WPjsc7SW2K7qPwH_E5OJ2lJDBafhEhs2fn_f6Kxbc9eZ6J7kgKyWAGvU-L54"

bot = Bot(TOKEN)
dp = Dispatcher()

print("2. Бот создан")

WELCOME_TEXT = """👋 Вас приветствует чат-бот-помощник по техническим олимпиадам!

Я помогу тебе:
• 🎯 выбрать подходящую олимпиаду
• ⏰ отслеживать важные дедлайны
• 📚 найти полезную информацию и материалы для подготовки

Просто выбери, что тебя интересует 👇"""

WELCOME_IMAGE = Path(__file__).parent / "привет.png"
OLYMPIADS_FILE = Path(__file__).parent / "olympiads.xlsx"   # ← файл с олимпиадами


DIRECTION_NAMES = {
    "informatics": "Информатика / ИКТ",
    "physics": "Физика",
    "math": "Математика",
    "chemistry": "Химия",
    "other": "Другие технические",
}

# Хранилище сохранённых олимпиад пользователей (в памяти)
# { user_id: [olympiad_id, ...] }
saved_olympiads: Dict[int, List[str]] = {}


# ==================== РАБОТА С EXCEL ====================

def load_olympiads() -> Dict[str, dict]:
    """Читает актуальные олимпиады из Excel"""
    try:
        # Читаем именно лист «Олимпиады»
        df = pd.read_excel(OLYMPIADS_FILE, sheet_name="Олимпиады", dtype=str)
        df = df.fillna("")

        # Валидные направления (чтобы отсечь строку-подсказку)
        valid_directions = {"informatics", "physics", "math", "chemistry", "other"}

        olympiads = {}
        for _, row in df.iterrows():
            oid = str(row["id"]).strip()
            direction = str(row["направление"]).strip()

            # Пропускаем пустые строки и строку-подсказку
            if not oid or direction not in valid_directions:
                continue

            olympiads[oid] = {
                "id": oid,
                "name": str(row["название"]).strip(),
                "direction": direction,
                "short_desc": str(row["описание"]).strip(),
                "deadline": str(row["дедлайн"]).strip(),
                "link": str(row["ссылка"]).strip(),
                "status": str(row["статус"]).strip(),
            }
        return olympiads
    except Exception as e:
        print(f"Ошибка чтения {OLYMPIADS_FILE}: {e}")
        return {}


def get_olympiads_by_direction(direction: str) -> List[dict]:
    olympiads = load_olympiads()
    return [o for o in olympiads.values() if o["direction"] == direction]


def get_olympiad(olymp_id: str) -> dict | None:
    olympiads = load_olympiads()
    return olympiads.get(olymp_id)


# ==================== КЛАВИАТУРЫ ====================

def get_main_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Выбор направления", payload="main:direction"))
    kb.row(CallbackButton(text="Сохранённые олимпиады", payload="main:saved"))
    kb.row(CallbackButton(text="FAQ", payload="main:faq"))
    return kb


def get_direction_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Информатика / ИКТ", payload="dir:informatics"))
    kb.row(CallbackButton(text="Физика", payload="dir:physics"))
    kb.row(CallbackButton(text="Математика", payload="dir:math"))
    kb.row(CallbackButton(text="Химия", payload="dir:chemistry"))
    kb.row(CallbackButton(text="Другие технические", payload="dir:other"))
    kb.row(CallbackButton(text="« Назад", payload="back:main"))
    return kb


def get_olympiads_list_keyboard(direction: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    olympiads = get_olympiads_by_direction(direction)
    for o in olympiads:
        title = o["name"]
        if len(title) > 40:
            title = title[:37] + "…"
        kb.row(CallbackButton(text=f"➡️ {title}", payload=f"olymp:{o['id']}"))
    kb.row(CallbackButton(text="« Назад", payload="back:direction"))
    return kb


def get_olympiad_card_keyboard(olymp_id: str, direction: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="💾 Сохранить в Мои олимпиады", payload=f"save:{olymp_id}"))
    kb.row(CallbackButton(text="🔄 Выбрать другую", payload=f"list:{direction}"))
    kb.row(CallbackButton(text="« Назад", payload=f"list:{direction}"))
    return kb


def get_saved_keyboard(user_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    user_saved = saved_olympiads.get(user_id, [])
    olympiads = load_olympiads()
    for oid in user_saved:
        o = olympiads.get(oid)
        if o:
            title = o["name"]
            if len(title) > 40:
                title = title[:37] + "…"
            kb.row(CallbackButton(text=f"📌 {title}", payload=f"olymp:{oid}"))
    kb.row(CallbackButton(text="« Назад", payload="back:main"))
    return kb


def get_back_to_main_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="« Назад", payload="back:main"))
    return kb


# ==================== ОТПРАВКА СООБЩЕНИЙ ====================

async def send_welcome(user_id: int | None = None, event: MessageCreated | MessageCallback | None = None):
    kb = get_main_keyboard()
    try:
        media = InputMedia(path=str(WELCOME_IMAGE))
        if isinstance(event, (MessageCreated, MessageCallback)):
            await event.message.answer(text=WELCOME_TEXT, attachments=[media, kb.as_markup()])
        elif user_id:
            await bot.send_message(user_id=user_id, text=WELCOME_TEXT, attachments=[media, kb.as_markup()])
    except Exception as e:
        print("Ошибка картинки:", e)
        if isinstance(event, (MessageCreated, MessageCallback)):
            await event.message.answer(text=WELCOME_TEXT, attachments=[kb.as_markup()])
        elif user_id:
            await bot.send_message(user_id=user_id, text=WELCOME_TEXT, attachments=[kb.as_markup()])


async def send_direction_menu(event: MessageCallback):
    text = (
        "🎯 Выбор направления\n\n"
        "Показываю только технические олимпиады "
        "(включая олимпиады Физтеха).\n\n"
        "Выбери направление:"
    )
    await event.message.answer(text=text, attachments=[get_direction_keyboard().as_markup()])


async def send_olympiads_list(event: MessageCallback, direction: str):
    name = DIRECTION_NAMES.get(direction, direction)
    olympiads = get_olympiads_by_direction(direction)

    if not olympiads:
        text = f"📌 Направление: {name}\n\nПока нет актуальных олимпиад в этом направлении."
        await event.message.answer(text=text, attachments=[get_direction_keyboard().as_markup()])
        return

    text = f"📌 Направление: {name}\n\nВыбери олимпиаду:"
    await event.message.answer(text=text, attachments=[get_olympiads_list_keyboard(direction).as_markup()])


async def send_olympiad_card(event: MessageCallback, olymp_id: str):
    o = get_olympiad(olymp_id)
    if not o:
        await event.message.answer(text="Олимпиада не найдена.")
        return

    text = (
        f"🏆 {o['name']}\n\n"
        f"{o['short_desc']}\n\n"
        f"📅 Дедлайн: {o['deadline']}\n"
        f"📊 Статус: {o['status']}\n"
        f"🔗 Сайт: {o['link']}"
    )
    await event.message.answer(
        text=text,
        attachments=[get_olympiad_card_keyboard(olymp_id, o["direction"]).as_markup()]
    )


# ==================== ХЕНДЛЕРЫ ====================

@dp.bot_started()
async def on_bot_started(event: BotStarted):
    print(f"user_id = {event.user.user_id}")
    await send_welcome(user_id=event.user.user_id)


@dp.message_created(Command("start"))
async def cmd_start(event: MessageCreated):
    await send_welcome(event=event)


@dp.message_callback()
async def on_callback(event: MessageCallback):
    payload = event.callback.payload
    user_id = event.callback.user.user_id
    print(f"user={user_id} payload={payload}")

    # ----- Навигация -----
    if payload == "back:main":
        await send_welcome(event=event)
        return

    if payload == "back:direction":
        await send_direction_menu(event)
        return

    # ----- Главное меню -----
    if payload == "main:direction":
        await send_direction_menu(event)

    elif payload == "main:saved":
        user_saved = saved_olympiads.get(user_id, [])
        if not user_saved:
            text = (
                "📌 Сохранённые олимпиады\n\n"
                "У тебя пока нет сохранённых олимпиад.\n\n"
                "Чтобы добавить:\n"
                "1. Зайди в «Выбор направления»\n"
                "2. Выбери олимпиаду\n"
                "3. Нажми «Сохранить в Мои олимпиады»"
            )
            await event.message.answer(text=text, attachments=[get_back_to_main_keyboard().as_markup()])
        else:
            text = "📌 Твои сохранённые олимпиады:\n\nВыбери, чтобы посмотреть подробнее:"
            await event.message.answer(text=text, attachments=[get_saved_keyboard(user_id).as_markup()])

    elif payload == "main:faq":
        await event.message.answer(
            text="❓ FAQ\n\nЗдесь будет меню базы знаний.",
            attachments=[get_back_to_main_keyboard().as_markup()]
        )

    # ----- Выбор направления → список -----
    elif payload.startswith("dir:"):
        direction = payload.split(":")[1]
        await send_olympiads_list(event, direction)

    # ----- Открыть список (для "Выбрать другую") -----
    elif payload.startswith("list:"):
        direction = payload.split(":")[1]
        await send_olympiads_list(event, direction)

    # ----- Карточка олимпиады -----
    elif payload.startswith("olymp:"):
        olymp_id = payload.split(":")[1]
        await send_olympiad_card(event, olymp_id)

    # ----- Сохранить олимпиаду -----
    elif payload.startswith("save:"):
        olymp_id = payload.split(":")[1]
        o = get_olympiad(olymp_id)
        if not o:
            await event.message.answer(text="Олимпиада не найдена.")
            return

        if user_id not in saved_olympiads:
            saved_olympiads[user_id] = []

        if olymp_id in saved_olympiads[user_id]:
            text = f"✅ «{o['name']}» уже сохранена в твоих олимпиадах."
        else:
            saved_olympiads[user_id].append(olymp_id)
            text = (
                f"✅ Олимпиада сохранена!\n\n"
                f"«{o['name']}»\n\n"
                f"Теперь бот сможет напоминать тебе о дедлайнах "
                f"и присылать обновления."
            )

        kb = InlineKeyboardBuilder()
        kb.row(CallbackButton(text="🔄 Выбрать другую", payload=f"list:{o['direction']}"))
        kb.row(CallbackButton(text="📌 Мои олимпиады", payload="main:saved"))
        kb.row(CallbackButton(text="« В главное меню", payload="back:main"))

        await event.message.answer(text=text, attachments=[kb.as_markup()])

    else:
        await event.message.answer(text="Неизвестная кнопка")


@dp.message_created()
async def echo(event: MessageCreated):
    text = (event.message.body.text or "").lower().strip()
    if text in ("привет", "hello", "start", "/start"):
        await send_welcome(event=event)
    else:
        await event.message.answer("Напиши /start или выбери кнопку в меню 👇")


async def main():
    print("3. Заходим в main()")
    # Проверяем наличие файла
    if not OLYMPIADS_FILE.exists():
        print(f"⚠ Файл {OLYMPIADS_FILE} не найден!")
    else:
        print(f"✓ Файл олимпиад найден: {OLYMPIADS_FILE}")
        print(f"  Загружено олимпиад: {len(load_olympiads())}")

    await bot.delete_webhook()
    print("4. Webhook удалён, запускаем polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("6. Запускаем asyncio")
    asyncio.run(main())