# app.py
import streamlit as st
import uuid, datetime, asyncio, json, pathlib
import aiosqlite
from openai import OpenAI


# -------------------- APIキーを JSON から読む --------------------

# OpenAIクライアントを作る
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# -------------------- SQLite 設定 -------------------------------
DB_PATH = "chat.db"

async def init_db():
    """存在しなければテーブルを作成"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            ts TEXT,
            metadata TEXT
        )
        """)
        await db.commit()

async def save_message(cid: str, role: str, content: str):
    """1 発言を SQLite に INSERT"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO messages(conversation_id, role, content, ts, metadata)
        VALUES (?,?,?,?,?)
        """, (cid, role, content,
              datetime.datetime.utcnow().isoformat(),
              "{}"))
        await db.commit()

asyncio.run(init_db())          # アプリ起動時にテーブルを準備

# -------------------- Streamlit UI ------------------------------
st.set_page_config(page_title="ChatAPP with SQLite", page_icon="💬")
st.title("ChatAPP_test")

# セッション変数
if "messages" not in st.session_state:
    st.session_state.messages = []
if "awaiting_reply" not in st.session_state:
    st.session_state.awaiting_reply = False
if "cid" not in st.session_state:
    st.session_state.cid = str(uuid.uuid4())    # ブラウザごとに固有 ID
cid = st.session_state.cid

# ---------- ユーザー入力 ----------
if prompt := st.chat_input("メッセージを入力してね"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    asyncio.run(save_message(cid, "user", prompt))
    st.session_state.awaiting_reply = True
    st.rerun()                                  # ユーザー発言を即表示

# ---------- これまでの会話を表示 ----------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- ChatGPT の返答 ----------
if st.session_state.awaiting_reply:
    full_reply = ""
    with st.chat_message("assistant"):
        with st.spinner("考え中..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                stream=True
            )
            placeholder = st.empty()
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                full_reply += content
                placeholder.markdown(full_reply + "▍")   # タイプ中カーソル
            placeholder.markdown(full_reply)             # カーソルを消す

    st.session_state.messages.append({"role": "assistant", "content": full_reply})
    asyncio.run(save_message(cid, "assistant", full_reply))
    st.session_state.awaiting_reply = False
    st.rerun()                                          # 会話を再描画