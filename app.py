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


# -------------------- 新: 会話要約機能 -------------------------------
SUMMARY_MODEL = "gpt-4o-mini"
MAX_MSG_FOR_SUMMARY = 30           # 負荷軽減のため直近 N 件のみ要約

async def generate_summary():
    """最新の会話を要約して st.session_state.summary に格納"""
    history = st.session_state.messages[-MAX_MSG_FOR_SUMMARY:]
    history_txt = "\n".join([f"{m['role']}: {m['content']}" for m in history])

    prompt = [
        {"role": "system",
         "content": "あなたは優秀な要約アシスタントです。次の会話を読んで、日本語で3〜5行に簡潔に要約してください。"},
        {"role": "user", "content": history_txt}
    ]

    res = client.chat.completions.create(
        model=SUMMARY_MODEL,
        messages=prompt
    )
    st.session_state.summary = res.choices[0].message.content.strip()


# -------------------- Streamlit UI ------------------------------
st.set_page_config(
    page_title="ChatAPP with SQLite", 
    page_icon="💬"
    )
st.title("ChatAPP_test")

# セッション変数
if "messages" not in st.session_state:
    st.session_state.messages = []
if "awaiting_reply" not in st.session_state:
    st.session_state.awaiting_reply = False
if "cid" not in st.session_state:
    st.session_state.cid = str(uuid.uuid4())    # ブラウザごとに固有 ID
if "summary" not in st.session_state:
    st.session_state.summary = "まだ要約はありません。"

cid = st.session_state.cid



# ───────────────────────────────────────────────────────────────────
# 1) サイドバー：ページ選択(任意)＋リアルタイム要約
with st.sidebar:
    st.subheader("📝 リアルタイム要約")
    st.markdown(st.session_state.get("summary", "まだ要約はありません。"))

# ───────────────────────────────────────────────────────────────────
# 2) メインエリアは 1 列だけに
chat_col = st.container()          # 右列(summary_col) を削除

prompt = st.chat_input("メッセージを入力してね")


# ───────────────────────────────────────────────────────────────────
# 3) チャット描画・返信ストリーム
with chat_col:
    # これまでの会話
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # アシスタント返信（元コードをほぼそのまま）
    if st.session_state.awaiting_reply:
        full_reply = ""
        with st.chat_message("assistant"):
            with st.spinner("考え中..."):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=st.session_state.messages,
                    stream=True,
                )
                placeholder = st.empty()
                for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    full_reply += content
                    placeholder.markdown(full_reply + "▍")
                placeholder.markdown(full_reply)

        # DB 保存 & 要約生成
        st.session_state.messages.append(
            {"role": "assistant", "content": full_reply}
        )
        asyncio.run(save_message(cid, "assistant", full_reply))
        asyncio.run(generate_summary())

        st.session_state.awaiting_reply = False
        st.rerun()

# ───────────────────────────────────────────────────────────────────
# 4) ユーザー入力があったら送信処理
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    asyncio.run(save_message(cid, "user", prompt))
    st.session_state.awaiting_reply = True
    st.rerun()