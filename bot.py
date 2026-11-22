import asyncio
import logging
from pathlib import Path

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, MessageCreated, Command
from maxapi.types.input_media import InputMedia

logging.basicConfig(level=logging.INFO)

print("1. Скрипт запустился")

TOKEN = "f9LHodD0cOLY1Zcn9BKB4KFO2weziKH1DRmeftPsM17OuWKsXnIu5BLOMD-cM5bKtJC1cMz7kw4Vje2p2P3y"  # ← обязательно вставь токен!

bot = Bot(TOKEN)
dp = Dispatcher()

print("2. Бот создан")

WELCOME_TEXT = """👋 Вас приветствует чат-бот-помощник по техническим олимпиадам!

Я помогу тебе:
• 🎯 выбрать подходящую олимпиаду
• ⏰ отслеживать важные дедлайны
• 📚 найти полезную информацию и материалы для подготовки

Просто выбери, что тебя интересует 👇"""

WELCOME_IMAGE = Path(__file__).parent / "привет.png"  # поменяй имя файла, если другое


@dp.bot_started()
async def on_bot_started(event: BotStarted):
    print("Пользователь нажал Начать")
    print(f"user_id = {event.user.user_id}")
    print(f"chat_id = {event.chat_id}")

    try:
        media = InputMedia(path=str(WELCOME_IMAGE))
        await bot.send_message(
            user_id=event.user.user_id,      # ← отправляем по user_id
            text=WELCOME_TEXT,
            attachments=[media]
        )
        print("Сообщение с картинкой отправлено")
    except Exception as e:
        print("Ошибка при отправке с картинкой:", e)
        try:
            await bot.send_message(
                user_id=event.user.user_id,
                text=WELCOME_TEXT
            )
            print("Текстовое сообщение отправлено")
        except Exception as e2:
            print("Ошибка и при отправке текста:", e2)

@dp.message_created(Command("start"))
async def cmd_start(event: MessageCreated):
    await event.message.answer("Бот работает!")


@dp.message_created()
async def echo(event: MessageCreated):
    text = (event.message.body.text or "").lower()
    if text in ("привет", "hello"):
        await event.message.answer("И тебе привет!")
    else:
        await event.message.answer("Напиши «привет»")


async def main():
    print("3. Заходим в main()")
    await bot.delete_webhook()
    print("4. Webhook удалён, запускаем polling...")
    await dp.start_polling(bot)
    print("5. Polling закончился (этого не должно быть)")


if __name__ == "__main__":
    print("6. Запускаем asyncio")
    asyncio.run(main())