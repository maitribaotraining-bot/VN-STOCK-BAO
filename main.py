import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import vnstock
import pandas as pd
import ta
import numpy as np

# ====================================
# CONFIG BOT TELEGRAM
# ====================================
BOT_TOKEN = "8937864972:AAGOMsxZOG7s6bKVW1al93ahQcfWU3lUYUg"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_news_sentiment(symbol):
    try:
        stock = vnstock.stock(symbol=symbol, source="VCI")
        df_news = stock.company.news()
        if df_news is None or df_news.empty:
            return "Trung lập", "Không có tin tức mới"
        
        latest_title = df_news['title'].iloc[0]
        negative = ['lỗ', 'giảm', 'phạt', 'cảnh báo', 'xấu']
        positive = ['lãi', 'tăng trưởng', 'vượt', 'ký kết', 'đạt']
        
        score = sum(1 for w in positive if w in latest_title.lower()) - sum(1 for w in negative if w in latest_title.lower())
        
        if score < 0: return "Tin xấu", latest_title
        elif score > 0: return "Tin tốt", latest_title
        return "Trung lập", latest_title
    except:
        return "Trung lập", "Không có tin tức mới"

def analyze_stock(df):
    df = df.sort_index(ascending=True).copy()
    close = pd.to_numeric(df["close"])
    
    rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]
    
    trend = "Uptrend" if close.iloc[-1] > close.iloc[-5] else "Downtrend"
    status = "Quá bán" if rsi < 30 else ("Quá mua" if rsi > 70 else "Bình thường")
    
    return round(close.iloc[-1], 2), trend, status, round(rsi, 2)

@dp.message()
async def handle_message(message: types.Message):
    symbol = message.text.strip().upper()
    if len(symbol) > 4 or not symbol.isalpha():
        await message.reply("❌ Mã chứng khoán không hợp lệ!")
        return

    wait_msg = await message.reply(f"🔄 Đang phân tích {symbol}...")
    
    try:
        df = vnstock.stock(symbol=symbol, source="VCI").quote.history(start="2026-01-01", end="2026-12-31", interval="1D")
        if df is None or df.empty:
            await bot.edit_message_text("❌ Không có dữ liệu.", chat_id=message.chat.id, message_id=wait_msg.message_id)
            return

        price, trend, status, rsi = analyze_stock(df)
        sentiment, title = get_news_sentiment(symbol)
        
        result = (
            f"**Mã: {symbol}**\n"
            f"Giá: {price}\n"
            f"Xu hướng: {trend}\n"
            f"RSI: {rsi} ({status})\n"
            f"Tin tức: {sentiment}\n"
            f"Tiêu đề: {title[:50]}..."
        )
        
        await bot.edit_message_text(result, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await bot.edit_message_text("❌ Lỗi hệ thống, thử lại sau...", chat_id=message.chat.id, message_id=wait_msg.message_id)

async def main():
    print("🤖 BOT ĐÃ ONLINE SẴN SÀNG...")
    # Dòng này là chìa khóa: skip_updates=True xóa bỏ mọi xung đột tin nhắn cũ bị treo
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
