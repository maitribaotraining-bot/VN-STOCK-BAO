import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import vnstock.stock as stock_module # Import module con
import pandas as pd
import ta
import numpy as np

BOT_TOKEN = "8937864972:AAGOMsxZOG7s6bKVW1al93ahQcfWU3lUYUg"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Hàm lấy dữ liệu giá lịch sử chuẩn cấu trúc mới
def get_stock_data(symbol):
    # Sử dụng module stock_module.price.history thay vì .stock()
    return stock_module.price.history(symbol=symbol, start="2026-01-01", end="2026-12-31", interval="1D")

@dp.message()
async def handle_message(message: types.Message):
    symbol = message.text.strip().upper()
    wait_msg = await message.reply("🔄 Đang phân tích...")
    try:
        df = get_stock_data(symbol)
        if df is None or df.empty:
            await bot.edit_message_text("❌ Không tìm thấy dữ liệu.", chat_id=message.chat.id, message_id=wait_msg.message_id)
            return

        # Phân tích kỹ thuật đơn giản
        close = pd.to_numeric(df["close"])
        price = round(close.iloc[-1], 2)
        
        result = f"**Mã: {symbol}**\nGiá hiện tại: {price}\n✅ Dữ liệu đã cập nhật thành công!"
        
        await bot.edit_message_text(result, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await bot.edit_message_text(f"❌ Lỗi: {str(e)}", chat_id=message.chat.id, message_id=wait_msg.message_id)

async def main():
    print("🤖 BOT ĐÃ ONLINE...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
