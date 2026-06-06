import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from vnstock import Vnstock
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
        stock = Vnstock().stock(symbol=symbol, source="VCI")
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
