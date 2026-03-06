import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 初始化
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_history():
    try:
        df = conn.read(ttl=0) 
        return df.dropna(subset=['role', 'content']).to_dict('records')
    except Exception as e:
        return []

# 2. UI 
st.title("No more simping, bonny! 🚑 ")
st.markdown("""
            <style>

                    /* 定位叉叉按鈕 */
                    .stButton>button {
                        position: absolute;
                        top: 30px;        /* 距離頂部 10 像素 */
                        border: none;
                        color: #ddd;      /* 平常淡淡的 */
                        font-size: 14px;
                        padding: 0;
                        width: 30px;
                        height: 30px;

                    }

            </style>
        """, unsafe_allow_html=True)
if "messages" not in st.session_state:
    st.session_state.messages = fetch_history()



for idx, msg in enumerate(st.session_state.messages):
        cols = st.columns([9, 1])
        
        with cols[0]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "timestamp" in msg:
                    st.caption(f"{msg['timestamp']}")
        
        with cols[1]:

            if st.button("🗑️", key=f"del_{idx}"):
                # 1. 從 session_state 移除該則訊息
                st.session_state.messages.pop(idx)
                
                # 2. 同步更新 Google Sheets
                try:
                    if len(st.session_state.messages) > 0:
                        new_df = pd.DataFrame(st.session_state.messages)
                        conn.update(data=new_df)
                    else:
                        # 如果刪光了，給一個空的 DataFrame
                        empty_df = pd.DataFrame(columns=['role', 'content', 'timestamp'])
                        conn.update(data=empty_df)
                    
                    # 3. 強制重新整理
                    st.rerun()
                except Exception as e:
                    st.error(f"雲端毀屍滅跡失敗：{e}")

# 3. 對話與存檔
if prompt := st.chat_input("他又做了什麼？"):

    # 取得當下精確時間
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 先顯示使用者訊息
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 格式化歷史紀錄
    api_contents = []
    for m in st.session_state.messages:
        role = "user" if m["role"] == "user" else "assistant"
        api_contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=str(m["content"]))]
            )
        )
    api_contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
    )

    response_text = "連 AI 都被氣到不想回了..."
    
    instruction = st.secrets["SYSTEM_INSTRUCTION"]

    # 3. 呼叫 Gemini
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=api_contents, # 歷史 + 現在
            config=types.GenerateContentConfig(
                system_instruction=instruction,
            )
        )
        response_text = response.text

    except Exception as e:
        response_text = f"🚨 發生錯誤：{str(e)}"
    
    # 4. 顯示助手回覆
    with st.chat_message("assistant"):
        st.markdown(response_text)
    
    # 存入 Session State
    st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    st.session_state.messages.append({"role": "assistant", "content": response_text, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    # 更新到 Sheets
    try:
        save_data = []
        for m in st.session_state.messages:
            save_data.append({
                "role": m["role"],
                "content": m["content"],
                "timestamp": m["timestamp"]
            })
        new_df = pd.DataFrame(save_data)
        conn.update(data=new_df)
    except Exception as e:
        st.warning(f"雲端存檔失敗：{e}")

