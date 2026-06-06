import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from vnstock import stock
import pandas as pd
import ta
import numpy as np

# Cấu hình log để anh xem trên Render
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = "8937864972:AAGOMsxZOG7s6bKVW1al93ahQcfWU3lUYUg"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message()
async def echo(message):
    try:
        symbol = message.text.strip().upper()
        # Gọi vnstock theo cấu trúc mới
        df = stock.quote.history(symbol=symbol, start="2026-01-01", end="2026-12-31", interval="1D")
        
        if df is not None and not df.empty:
            price = df['close'].iloc[-1]
            await message.reply(f"📈 Mã {symbol} giá hiện tại: {price}")
        else:
            await message.reply("❌ Không tìm thấy dữ liệu.")
    except Exception as e:
        await message.reply(f"⚠️ Lỗi: {str(e)}")

async def main():
    # skip_updates=True loại bỏ xung đột Telegram
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
