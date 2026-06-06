import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from vnstock import vnstock
import pandas as pd
import ta
import numpy as np
import requests
import time

# ====================================
# CONFIG BOT TELEGRAM (FAQ FOR CLIENTS)
# ====================================
BOT_TOKEN = "8937864972:AAGOMsxZOG7s6bKVW1al93ahQcfWU3lUYUg"

# Khởi tạo Bot và Dispatcher chuẩn Async
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_news_sentiment(symbol):
    try:
        # Đồng bộ cú pháp vnstock viết thường bản mới nhất
        stock = vnstock().stock(symbol=symbol, source="VCI")
        df_news = stock.company.news()
        if df_news is None or df_news.empty:
            return "Trung lập", "Không có tin tức mới nổi bật"
        latest_title = df_news['title'].iloc[0]
        
        negative_words = ['lỗ', 'giảm', 'phạt', 'cảnh báo', 'chậm', 'hủy', 'thanh tra', 'đình chỉ', 'xấu', 'vướng mắc']
        positive_words = ['lãi', 'tăng trưởng', 'vượt', 'ký kết', 'đạt', 'doanh thu', 'xuất khẩu', 'lợi nhuận', 'trúng thầu']
        
        score = 0
        for word in negative_words:
            if word in latest_title.lower(): score -= 1
        for word in positive_words:
            if word in latest_title.lower(): score += 1
                
        if score < 0: return "Tin xấu", latest_title
        elif score > 0: return "Tin tốt", latest_title
        return "Trung lập", latest_title
    except:
        return "Trung lập", "Không có tin tức mới nổi bật"

def analyze_multi_timeframe(df):
    df_daily = df.sort_index(ascending=True).copy()
    df_daily['time'] = pd.to_datetime(df_daily['time'])
    df_daily.set_index('time', inplace=True)
    
    # Khung tuần (1W)
    df_weekly = df_daily['close'].resample('W').last().to_frame()
    df_weekly['ema20'] = ta.trend.EMAIndicator(close=df_weekly['close'], window=20).ema_indicator()
    trend_1w = "Uptrend" if len(df_weekly) >= 2 and df_weekly['close'].iloc[-1] > df_weekly['ema20'].iloc[-1] else "Downtrend"

    # Khung ngày (1D)
    close_d = pd.to_numeric(df_daily["close"])
    rsi_series = ta.momentum.RSIIndicator(close=close_d, window=14).rsi()
    stoch_rsi_obj = ta.momentum.StochasticRSIIndicator(close=close_d, window=14, smooth1=3, smooth2=3)
    stoch_k = stoch_rsi_obj.stochrsi_k() * 100
    stoch_d_val = stoch_rsi_obj.stochrsi_d() * 100
    
    # Giả lập Banker
    rsi_mcdx = ta.momentum.RSIIndicator(close=close_d, window=20).rsi()
    banker_series = np.clip(np.where(rsi_mcdx > 50, (rsi_mcdx - 50) * 2, 0), 0, 100)
    
    latest_price = round(close_d.iloc[-1], 2)
    latest_rsi = round(rsi_series.iloc[-1], 2)
    latest_k = round(stoch_k.iloc[-1], 2)
    latest_d = round(stoch_d_val.iloc[-1], 2)
    latest_banker = round(banker_series[-1], 2)
    
    status_1d = "Quá bán" if latest_rsi < 30 else ("Tín hiệu đáy" if latest_k < 20 and latest_k > latest_d else "Bình thường")

    # Mô phỏng hành vi hành động giá
    match_count, success_count = 0, 0
    for i in range(50, len(df_daily) - 5):
        if abs(rsi_series.iloc[i] - latest_rsi) < 5 and abs(banker_series[i] - latest_banker) < 10:
            match_count += 1
            if (close_d.iloc[i+5] - close_d.iloc[i]) / close_d.iloc[i] > 0.02: success_count += 1
                
    win_rate = round((success_count / match_count) * 100, 2) if match_count > 0 else 50.0
    return latest_price, trend_1w, status_1d, latest_rsi, latest_k, latest_banker, win_rate

# ====================================
# XỬ LÝ LẮNG NGHE TIN NHẮN TỪ KHÁCH HÀNG
# ====================================
@dp.message()
async def reply_stock_analysis(message: types.Message):
    symbol = message.text.strip().upper()
    
    if len(symbol) != 3 or not symbol.isalpha():
        await message.reply("❌ Vui lòng nhập đúng mã cổ phiếu cần tra cứu (Ví dụ: HPG, SSI, FRT)...")
        return
        
    waiting_msg = await message.reply(f"🔄 Đang kết nối dữ liệu hệ thống để phân tích mã {symbol}, anh/chị chờ em vài giây...")

    try:
        loop = asyncio.get_event_loop()
        # Đồng bộ cú pháp vnstock viết thường bản mới nhất
        stock = vnstock().stock(symbol=symbol, source="VCI")
        df = await loop.run_in_executor(None, lambda: stock.quote.history(start="2023-01-01", end="2026-12-31", interval="1D"))
        
        if df is None or len(df) < 100:
            await bot.edit_message_text(
                text=f"❌ Không tìm thấy dữ liệu giao dịch cho mã {symbol}. Anh/chị vui lòng kiểm tra lại mã.",
                chat_id=message.chat.id,
                message_id=waiting_msg.message_id
            )
            return
            
        price, trend_1w, status_1d, rsi, stoch_k, banker, sim_prob = await loop.run_in_executor(
            None, analyze_multi_timeframe, df
        )
        sentiment, news_title = await loop.run_in_executor(None, get_news_sentiment, symbol)
        
        if trend_1w == "Uptrend" and banker > 20:
            if sentiment == "Tin xấu":
                verdict = "MUA GOM - Tin xấu ra để đè giá, cá mập âm thầm hấp thụ hết lực bán, cơ hội gom giá tốt."
            else:
                verdict = "MUA GOM - Xu hướng lớn ủng hộ, cá mập đang đẩy tiền gom hàng, xác suất nổ tím cao."
            decision_icon = "🟪"
        elif trend_1w == "Downtrend":
            verdict = f"THEO DÕI - Khung tuần xấu, rủi ro dính bẫy giá tăng (Bull-trap) do tin tức {sentiment.lower()} bủa vây."
            decision_icon = "🟡"
        else:
            verdict = "THEO DÕI - Cổ phiếu đang tích lũy đi ngang, chờ dòng tiền bùng nổ rõ ràng hơn."
            decision_icon = "🟡"

        reply_text = (
            f"**{symbol} -> Giá: {price}**\n"
            f"+ 🌐 Đa khung: Tuần (1W): {trend_1w} | Ngày (1D): {status_1d}\n"
            f"+ 📊 Kỹ thuật: RSI: {rsi} | StochK: {stoch_k} | Banker: {banker}%\n"
            f"+ 📰 Tin tức: **{sentiment}** ({news_title[:45]}...)\n"
            f"+ 📈 Mô phỏng: Xác suất tăng giá 5 phiên tới: {sim_prob}%\n"
            f"+ {decision_icon} Nhận định: {verdict}"
        )
        
        await bot.edit_message_text(
            text=reply_text,
            chat_id=message.chat.id,
            message_id=waiting_msg.message_id,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        print(f"Lỗi hệ thống: {e}")
        await bot.edit_message_text(
            text=f"❌ Hệ thống bận hoặc mã {symbol} không hợp lệ, vui lòng thử lại sau ít phút.",
            chat_id=message.chat.id,
            message_id=waiting_msg.message_id
        )

# ====================================
# RUN ASYNC POLLING
# ====================================
async def main():
    print("🤖 BOT CHAT FAQ CHO KHÁCH HÀNG ĐÃ ONLINE (CHẠY ASYNC 24/7)...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
