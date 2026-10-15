from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import io
import json
import logging
import os
import re
import sqlite3
import tempfile
import urllib.parse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import chromadb
from duckduckgo_search import DDGS
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from groq import Groq
from playwright.async_api import async_playwright
from pypdf import PdfReader
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import uvicorn
from youtube_transcript_api import YouTubeTranscriptApi

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
PORT = int(os.environ.get("PORT", 8080))

# Initialize Groq & ChromaDB Vector Store
groq_client = Groq(api_key=GROQ_API_KEY)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
knowledge_collection = chroma_client.get_or_create_collection(
    name="personal_knowledge"
)

telegram_app: Application = None
scheduler = AsyncIOScheduler()
DB_NAME = "bot_memory.db"


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
  conn.commit()
  conn.close()


init_db()

SYSTEM_PROMPT = """أنت مساعد ذكي ومتقدم ومنسق لفريق من الوكلاء المتخصصين (Multi-Agent System).
- التاريخ الحالي هو: 15 أكتوبر 2026.
- لديك أدوات متقدمة تشمل: RAG (قاعدة المعرفة)، Text-to-SQL (استعلام قواعد البيانات)، Playwright (المتصفح والأتمتة)، البحث العميق، يوتيوب، غيت هب، وتوليد الملفات.
- نسق بين الوكلاء بدقة لتقديم أفضل إجابة تحليلية للمستخدم.
"""


def get_history(user_id: int, limit: int = 10):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC"
      " LIMIT ?",
      (user_id, limit * 2),
  )
  rows = cursor.fetchall()
  conn.close()
  rows.reverse()
  history = [{"role": "system", "content": SYSTEM_PROMPT}]
  for role, content in rows:
    if role in ["user", "assistant"]:
      history.append({"role": role, "content": content})
  return history


def save_message(user_id: int, role: str, content: str):
  if not content:
    return
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
      (user_id, role, content),
  )
  conn.commit()
  conn.close()


# --- TOOLS DEFINITION FOR GROQ FUNCTION CALLING ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for real-time information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_personal_rag",
            "description": (
                "Search user's personal uploaded knowledge base (RAG)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term in personal documents.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_text_to_sql",
            "description": (
                "Execute a SQL query against the bot's SQLite database to"
                " analyze messages or data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": (
                            "SQL query (e.g., SELECT * FROM messages LIMIT 5)"
                        ),
                    }
                },
                "required": ["sql_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browse_website_with_playwright",
            "description": (
                "Open a website using Playwright browser, extract text, or take"
                " screenshot."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to browse.",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_youtube",
            "description": "Summarize YouTube video transcript.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "YouTube URL."}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_repo_action",
            "description": "Read file or search code in GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "search"],
                    },
                    "repo": {
                        "type": "string",
                        "description": "owner/repo",
                    },
                    "path": {"type": "string"},
                },
                "required": ["action", "repo", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_and_send_file",
            "description": "Generate a file and send it to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["filename", "content"],
            },
        },
    },
]


# --- TOOL IMPLEMENTATIONS ---
def search_web(query: str) -> str:
  try:
    with DDGS() as ddgs:
      results = [r for r in ddgs.text(query, max_results=3)]
      if results:
        return "\n".join(
            [
                f"- {r.get('title')}: {r.get('body')} ({r.get('href')})"
                for r in results
            ]
        )
      return "لا توجد نتائج."
  except Exception as e:
    return f"خطأ: {e}"


def query_personal_rag(query: str) -> str:
  try:
    results = knowledge_collection.query(query_texts=[query], n_results=3)
    docs = results.get("documents", [[]])[0]
    if docs:
      return "مستندات ذات صلة من قاعدة المعرفة:\n" + "\n".join(docs)
    return "لا توجد معلومات مطابقة في قاعدة المعرفة الشخصية."
  except Exception as e:
    return f"خطأ RAG: {e}"


def execute_text_to_sql(sql_query: str) -> str:
  try:
    # حماية بسيطة للاستعلامات
    if not sql_query.strip().lower().startswith("select"):
      return "مسموح فقط باستعلامات القراءة (SELECT)."
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    conn.close()
    return f"نتائج قاعدة البيانات:\n{json.dumps(rows, ensure_ascii=False)}"
  except Exception as e:
    return f"خطأ في تنفيذ SQL: {e}"


async def browse_website_with_playwright(url: str) -> str:
  try:
    async with async_playwright() as p:
      browser = await p.chromium.launch(headless=True)
      page = await browser.new_page()
      await page.goto(url, timeout=30000)
      content = await page.inner_text("body")
      await browser.close()
      return content[:10000]
  except Exception as e:
    return f"خطأ Playwright: {e}"


def summarize_youtube(url: str) -> str:
  try:
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if not match:
      return "رابط غير صالح."
    video_id = match.group(1)
    transcript = YouTubeTranscriptApi.get_transcript(
        video_id, languages=["ar", "en"]
    )
    return " ".join([t["text"] for t in transcript])[:12000]
  except Exception as e:
    return f"خطأ يوتيوب: {e}"


def github_repo_action(action: str, repo: str, path: str = "") -> str:
  headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
  try:
    if action == "read":
      res = requests.get(
          f"https://api.github.com/repos/{repo}/contents/{path}", headers=headers
      )
      if res.status_code == 200:
        download_url = res.json().get("download_url")
        return requests.get(download_url).text if download_url else ""
    elif action == "search":
      res = requests.get(
          f"https://api.github.com/search/code?q={path}+repo:{repo}",
          headers=headers,
      )
      if res.status_code == 200:
        return json.dumps(
            [i.get("path") for i in res.json().get("items", [])],
            ensure_ascii=False,
        )
    return "فشل العملية"
  except Exception as e:
    return f"خطأ GitHub: {e}"


async def generate_and_send_file_tool(
    chat_id: int, filename: str, content: str
) -> str:
  try:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, suffix=f"_{filename}"
    ) as f:
      f.write(content)
      temp_path = f.name
    with open(temp_path, "rb") as f_doc:
      await telegram_app.bot.send_document(
          chat_id=chat_id, document=f_doc, filename=filename
      )
    os.unlink(temp_path)
    return f"تم إرسال الملف {filename} بنجاح."
  except Exception as e:
    return f"خطأ ملف: {e}"


# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  await update.message.reply_text(
      "🤖 أهلاً بك! تم ترقية البوت بنجاح ليعمل بنظام **Multi-Agent** متكامل مع"
      " RAG, Text-to-SQL, و Playwright Browser!"
  )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  await update.message.reply_text(
      "📚 ميزات النظام:\n- RAG (قاعدة المعرفة للملفات المرفوعة)\n- SQL Agent"
      " (تحليل قاعدة البيانات)\n- Playwright (تصفح المواقع الحية)\n- يوتيوب وغيت"
      " هب وتوليد الملفات"
  )


async def draw_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
  args = context.args
  if not args:
    return
  prompt = " ".join(args)
  image_url = (
      f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
  )
  await update.message.reply_photo(photo=image_url, caption=prompt)


async def remind_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
  try:
    args = context.args
    seconds, reminder_text = int(args[0]), " ".join(args[1:])
    chat_id = update.effective_chat.id
    scheduler.add_job(
        lambda: telegram_app.bot.send_message(
            chat_id=chat_id, text=f"⏰ تذكير: {reminder_text}"
        ),
        "date",
        run_date=datetime.now() + timedelta(seconds=seconds),
    )
    await update.message.reply_text(f"✅ تم جدولة التذكير بعد {seconds} ثانية.")
  except Exception as e:
    await update.message.reply_text(f"خطأ: {e}")


async def process_ai_response(
    update: Update, user_id: int, message_text: str
):
  await update.message.chat.send_action(action="typing")
  chat_id = update.effective_chat.id

  history = get_history(user_id, limit=10)
  history.append({"role": "user", "content": message_text})
  save_message(user_id, "user", message_text)

  try:
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=history,
        tools=tools,
        tool_choice="auto",
        max_tokens=2048,
        temperature=0.7,
    )
    res_msg = response.choices[0].message

    if res_msg.tool_calls:
      history.append(res_msg)
      for call in res_msg.tool_calls:
        name, args = call.function.name, json.loads(call.function.arguments)
        res = ""
        if name == "search_web":
          res = search_web(args.get("query"))
        elif name == "query_personal_rag":
          res = query_personal_rag(args.get("query"))
        elif name == "execute_text_to_sql":
          res = execute_text_to_sql(args.get("sql_query"))
        elif name == "browse_website_with_playwright":
          res = await browse_website_with_playwright(args.get("url"))
        elif name == "summarize_youtube":
          res = summarize_youtube(args.get("url"))
        elif name == "github_repo_action":
          res = github_repo_action(
              args.get("action"), args.get("repo"), args.get("path", "")
          )
        elif name == "generate_and_send_file":
          res = await generate_and_send_file_tool(
              chat_id, args.get("filename"), args.get("content")
          )

        history.append({
            "tool_call_id": call.id,
            "role": "tool",
            "name": name,
            "content": res,
        })

      second_res = groq_client.chat.completions.create(
          model=GROQ_MODEL, messages=history, max_tokens=2048
      )
      ai_response = second_res.choices[0].message.content
    else:
      ai_response = res_msg.content

    save_message(user_id, "assistant", ai_response)
    if ai_response:
      await update.message.reply_text(ai_response)
  except Exception as e:
    await update.message.reply_text(f"❌ خطأ: {e}")


async def handle_document(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
  document = update.message.document
  user_id = update.effective_user.id
  file_name = document.file_name
  try:
    file_bytes = await (await document.get_file()).download_as_bytearray()
    text = (
        "".join([p.extract_text() for p in PdfReader(io.BytesIO(file_bytes)).pages])
        if file_name.endswith(".pdf")
        else file_bytes.decode("utf-8", errors="ignore")
    )

    # حفظ الملف في قاعدة المعرفة (RAG)
    knowledge_collection.add(
        documents=[text[:5000]],
        ids=[f"{user_id}_{datetime.now().timestamp()}"],
    )
    await update.message.reply_text(
        f"📂 تم حفظ الملف `{file_name}` في قاعدة المعرفة (RAG) بنجاح!"
    )
  except Exception as e:
    await update.message.reply_text(f"❌ خطأ ملف: {e}")


async def handle_voice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
  try:
    file_bytes = await (await update.message.voice.get_file()).download_as_bytearray()
    transcription = groq_client.audio.transcriptions.create(
        file=("voice.ogg", bytes(file_bytes)), model="whisper-large-v3"
    )
    await process_ai_response(
        update, update.effective_user.id, transcription.text
    )
  except Exception as e:
    await update.message.reply_text(f"❌ خطأ صوتي: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  await process_ai_response(
      update, update.effective_user.id, update.message.text
  )


async def init_telegram_bot():
  global telegram_app
  telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
  telegram_app.add_handler(CommandHandler("start", start))
  telegram_app.add_handler(CommandHandler("help", help_command))
  telegram_app.add_handler(CommandHandler("draw", draw_command))
  telegram_app.add_handler(CommandHandler("remind", remind_command))
  telegram_app.add_handler(
      MessageHandler(filters.Document.ALL, handle_document)
  )
  telegram_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
  telegram_app.add_handler(
      MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
  )
  scheduler.start()
  await telegram_app.initialize()
  await telegram_app.start()
  await telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)


@asynccontextmanager
async def lifespan(app: FastAPI):
  await init_telegram_bot()
  yield
  if telegram_app:
    scheduler.shutdown()
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()


app = FastAPI(title="Enterprise Multi-Agent Telegram Bot", lifespan=lifespan)


@app.get("/")
async def health_check():
  return JSONResponse({"status": "healthy", "service": "Enterprise AI Agent"})


def main():
  uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
  main()
