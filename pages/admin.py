import streamlit as st
import aiosqlite, asyncio, pandas as pd

DB_PATH = "chat.db"

# ---------- DB helper ----------
async def fetch_conversations() -> pd.DataFrame:
    query = """
    SELECT conversation_id,
           MIN(ts)  AS first_ts,
           MAX(ts)  AS last_ts,
           COUNT(*) AS msg_count
    FROM messages
    GROUP BY conversation_id
    ORDER BY last_ts DESC;
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(query)
        return pd.DataFrame([dict(r) for r in rows])      # ← 変更

async def fetch_messages(cid: str) -> pd.DataFrame:
    query = """
    SELECT role, content, ts
    FROM messages
    WHERE conversation_id = ?
    ORDER BY id;
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(query, (cid,))
        return pd.DataFrame([dict(r) for r in rows])      # ← 変更

# ---------- UI ----------
st.set_page_config(page_title="Chat Logs Admin", page_icon="📋")
st.title("📋 Chat Logs (Admin)")

conv_df = asyncio.run(fetch_conversations())

if conv_df.empty:
    st.info("まだチャットログがありません。アプリで会話した後に再読込してください。")
    st.stop()

st.subheader("🗂 会話一覧")
st.dataframe(
    conv_df,
    hide_index=True,
    column_config={
        "conversation_id": "Conversation ID",
        "first_ts":       "First Msg",
        "last_ts":        "Last Msg",
        "msg_count":      "Msgs",
    },
    use_container_width=True,
)

# Conversation ID プルダウン
cid = st.selectbox(
    "詳細を表示したい Conversation ID を選択してください",
    options=conv_df["conversation_id"],
    format_func=lambda x: f"{x[:8]}…  ({int(conv_df.loc[conv_df.conversation_id==x,'msg_count'])} msgs)"
)

# 詳細表示
if cid:
    st.divider()
    st.subheader(f"📑 会話詳細 : {cid}")
    msgs = asyncio.run(fetch_messages(cid))

    if msgs.empty:
        st.warning("発言が見つかりませんでした。")
    else:
        for _, r in msgs.iterrows():
            with st.chat_message(r.role):
                st.markdown(f"{r.content}\n\n<small>{r.ts}</small>", unsafe_allow_html=True)

        csv = msgs.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ CSV でダウンロード",
            csv,
            file_name=f"{cid}.csv",
            mime="text/csv"
        )
