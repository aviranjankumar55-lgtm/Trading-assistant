# भारतीय शेयर ट्रेडिंग असिस्टेंट (प्रोटोटाइप)
# इंस्टॉल:  pip install streamlit yfinance pandas google-genai
# चलाएँ:    streamlit run trading_assistant.py
# पहले अपनी Gemini API key सेट करें: GEMINI_API_KEY

import os
from google import genai
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="ट्रेडिंग असिस्टेंट", layout="wide")
st.title("📈 भारतीय शेयर ट्रेडिंग असिस्टेंट")
st.caption("सिर्फ़ सीखने और जाँचने के लिए। यह वित्तीय सलाह नहीं है।")

symbol = st.text_input("शेयर सिंबल (NSE के लिए .NS, जैसे RELIANCE.NS)", "RELIANCE.NS")
period = st.selectbox("अवधि", ["3mo", "6mo", "1y"], index=1)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    df["RSI"] = 100 - 100 / (1 + gain / loss)
    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9).mean()
    return df


def get_news(ticker: yf.Ticker) -> list[str]:
    titles = []
    try:
        for item in ticker.news[:8]:
            title = item.get("content", {}).get("title") or item.get("title")
            if title:
                titles.append(title)
    except Exception:
        pass
    return titles


if st.button("विश्लेषण करो"):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period)
    if data.empty:
        st.error("डेटा नहीं मिला। सिंबल जाँचिए।")
        st.stop()

    data = add_indicators(data)
    st.line_chart(data[["Close", "SMA20", "SMA50"]])
    st.line_chart(data[["RSI"]])

    news = get_news(ticker)
    last = data.tail(10)[["Close", "SMA20", "SMA50", "RSI", "MACD", "MACD_signal"]].round(2)

    prompt = f"""तुम एक अनुभवी भारतीय शेयर बाज़ार विश्लेषक हो।
शेयर: {symbol}
पिछले 10 दिनों का डेटा और इंडिकेटर:
{last.to_string()}

ताज़ा न्यूज़ हेडलाइन:
{chr(10).join('- ' + n for n in news) or 'कोई न्यूज़ नहीं मिली'}

हिंदी में बताओ:
1. ट्रेंड (ऊपर/नीचे/साइडवेज़) और कारण
2. इंडिकेटर क्या संकेत दे रहे हैं
3. न्यूज़ का असर
4. सुझाव: खरीदें / बेचें / इंतज़ार करें, साथ में स्टॉप-लॉस का विचार और जोखिम
अंत में साफ़ लिखो कि यह गारंटी नहीं, सिर्फ़ विश्लेषण है।"""

    try:
        api_key = os.environ["GEMINI_API_KEY"]
        model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        client = genai.Client(api_key=api_key)
        reply = client.models.generate_content(model=model, contents=prompt)
        st.subheader("AI विश्लेषण")
        st.write(reply.text)
    except KeyError:
        st.error("GEMINI_API_KEY सेट नहीं है।")
    except Exception as e:
        st.error(f"AI से जवाब नहीं आया। मॉडल का नाम या चाबी जाँचिए। ब्योरा: {e}")

    if news:
        st.subheader("ताज़ा न्यूज़")
        for n in news:
            st.write("•", n)
