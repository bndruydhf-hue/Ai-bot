from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import asyncio
import io
import json
import logging
import os
import re
import sqlite3
import tempfile
import urllib.parse
from pathlib import Path

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from duckduckgo_search import DDGS
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from groq import AsyncGroq
from pypdf import PdfReader
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


# ----------------------------- Logging ---------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("stable_ai_agent")

# ----------------------------- Configuration ---------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
PORT = int(os.getenv("PORT", "8080"))
DB_NAME = os.getenv("DB_NAME", "bot_memory.db")

if not TELEGRAM_TOKEN:
    logger.warning("TELEGRAM_TOKEN is not configured.")
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY is not configured.")

groq_client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
telegram_app: Application | None = None
scheduler = AsyncIOScheduler()

SYSTEM_PROMPT = """أنت مساعد ذكي على تيليجرام وتجيب باللغة التي يستخدمها المستخدم، ويفضل العربية إذا كتب بالعربية.
التاريخ الحالي: 15 أكتوبر 2026.
لديك أداة بحث على الإنترنت اسمها search_web، لكنها ليست متصفحًا رسوميًا.
- استخدم البحث عند السؤال عن الأسعار الحالية، المنتجات، الأخبار، أو أي معلومة حديثة.
- لا تخترع الأسعار أو نتائج البحث. إذا لم تجد سعرًا موثوقًا، وضّح ذلك واذكر المصادر المتاحة.
- لخّص النتائج بوضوح، وأرفق الروابط التي رجعت من البحث.
- إذا فشل البحث، قل للمستخدم إن البحث تعذّر بدل الادعاء بأنك بحثت.
- لا تدّعِ أنك نفّذت إجراءً لم تنفّذه بالفعل.
"""

# ----------------------------- Database --------------------------------------
def init_db() -> None:
    with sqlite3.connect(DB_NAME, timeout=15) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_user_id_id "
            "ON messages(user_id, id)"
        )


def get_history(user_id: int, limit: int = 10) -> list[dict]:
    with sqlite3.connect(DB_NAME, timeout=15) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit * 2),
        ).fetchall()

    rows.reverse()
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    for role, content in rows:
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
    return history


def save_message(user_id: int, role: str, content: str | None) -> None:
    if not content:
        return
    with sqlite3.connect(DB_NAME, timeout=15) as conn:
        conn.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )


init_db()

# ----------------------------- Tool definitions ------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the live web for current facts, product prices, "
                "news, and sources. Use this when information may have changed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Specific search query, preferably including country/currency when relevant.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_youtube",
            "description": "Get the available transcript of a YouTube video.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_repo_action",
            "description": "Read a file or search code in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["read", "search"]},
                    "repo": {"type": "string", "description": "owner/repo"},
                    "path": {
                        "type": "string",
                        "description": "File path for read, or code search query for search.",
                    },
                },
                "required": ["action", "repo", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_and_send_file",
            "description": "Create a text file and send it to the current Telegram chat.",
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

# ----------------------------- Tools -----------------------------------------
async def search_web(query: str) -> str:
    """Search DuckDuckGo live and return concise results without any API key."""
    query = (query or "").strip()
    if not query:
        return "لم يتم توفير عبارة بحث."

    try:
        results = []
        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=5))

        raw_results = await asyncio.to_thread(_search)
        
        for r in raw_results:
            title = str(r.get("title", "")).strip()
            body = str(r.get("body", "")).strip()
            href = str(r.get("href", "")).strip()
            
            result = f"العنوان: {title}\nالمعلومات: {body}"
            if href:
                result += f"\nالرابط: {href}"
            results.append(result)

        if results:
            return "\n\n".join(results)[:10000]
        return "لم تظهر نتائج بحث."
        
    except Exception:
        logger.exception("DuckDuckGo search failed")
        return "تعذّر البحث على الإنترنت بسبب خطأ تقني."


def _youtube_transcript_sync(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([0-9A-Za-z_-]{11})", url)
    if not match:
        return "رابط يوتيوب غير صالح أو لم أستطع استخراج معرّف الفيديو."
    video_id = match.group(1)
    try:
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):
            transcript = api.fetch(video_id, languages=["ar", "en"])
            snippets = getattr(transcript, "snippets", transcript)
            parts = []
            for item in snippets:
                if isinstance(item, dict):
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(getattr(item, "text", "")))
            text = " ".join(p for p in parts if p)
        else:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["ar", "en"]
            )
            text = " ".join(str(t.get("text", "")) for t in transcript)
        return text[:12000] or "لم يتوفر نص للفيديو."
    except Exception as exc:
        logger.warning("YouTube transcript failed: %s", exc)
        return "تعذّر استخراج نص الفيديو؛ قد لا تكون الترجمة متاحة."


async def summarize_youtube(url: str) -> str:
    return await asyncio.to_thread(_youtube_transcript_sync, url)


async def github_repo_action(action: str, repo: str, path: str = "") -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo or ""):
        return "اسم المستودع غير صالح. استخدم owner/repo."
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            if action == "read":
                encoded_path = urllib.parse.quote(path or "", safe="/")
                response = await client.get(
                    f"https://api.github.com/repos/{repo}/contents/{encoded_path}",
                    headers=headers,
                )
                if response.status_code != 200:
                    return f"تعذرت قراءة الملف من GitHub (HTTP {response.status_code})."
                payload = response.json()
                if payload.get("type") != "file":
                    return "المسار ليس ملفًا واحدًا. حدّد مسار الملف المطلوب."
                download_url = payload.get("download_url")
                if not download_url:
                    return "لم يرجع GitHub رابط تنزيل للملف."
                file_response = await client.get(download_url)
                file_response.raise_for_status()
                return file_response.text[:15000]

            if action == "search":
                params = {"q": f"{path} repo:{repo}"}
                response = await client.get(
                    "https://api.github.com/search/code",
                    params=params,
                    headers=headers,
                )
                if response.status_code != 200:
                    return (
                        f"تعذر البحث في GitHub (HTTP {response.status_code}). "
                        "قد يتطلب بحث الكود توكن GitHub وصلاحية مناسبة."
                    )
                items = response.json().get("items", [])
                return json.dumps(
                    [
                        {"path": item.get("path"), "html_url": item.get("html_url")}
                        for item in items[:20]
                    ],
                    ensure_ascii=False,
                )
            return "الإجراء غير مدعوم."
    except Exception:
        logger.exception("GitHub operation failed")
        return "حدث خطأ أثناء الاتصال بـ GitHub."


async def generate_and_send_file_tool(
    chat_id: int, filename: str, content: str
) -> str:
    if telegram_app is None:
        return "بوت تيليجرام غير جاهز لإرسال الملف."

    safe_name = Path(filename or "file.txt").name
    if not safe_name or safe_name in (".", ".."):
        safe_name = "file.txt"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            delete=False,
            suffix="_" + safe_name,
        ) as temp_file:
            temp_file.write(content or "")
            temp_path = temp_file.name

        with open(temp_path, "rb") as file_obj:
            await telegram_app.bot.send_document(
                chat_id=chat_id,
                document=file_obj,
                filename=safe_name,
            )
        return f"تم إرسال الملف {safe_name} بنجاح."
    except Exception:
        logger.exception("File generation/send failed")
        return "تعذّر إنشاء الملف أو إرساله عبر تيليجرام."
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("Could not remove temporary file: %s", temp_path)


async def execute_tool(name: str, args: dict, chat_id: int) -> str:
    try:
        if name == "search_web":
            return await search_web(args.get("query", ""))
        if name == "summarize_youtube":
            return await summarize_youtube(args.get("url", ""))
        if name == "github_repo_action":
            return await github_repo_action(
                args.get("action", ""),
                args.get("repo", ""),
                args.get("path", ""),
            )
        if name == "generate_and_send_file":
            return await generate_and_send_file_tool(
                chat_id,
                args.get("filename", "file.txt"),
                args.get("content", ""),
            )
        return f"الأداة غير معروفة: {name}"
    except Exception:
        logger.exception("Tool execution failed: %s", name)
        return f"تعذر تنفيذ الأداة {name} بسبب خطأ تقني."


# ----------------------------- Telegram handlers -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "🤖 أهلًا بك! البوت جاهز. أرسل سؤالك، وسأبحث على الإنترنت عندما يحتاج السؤال إلى معلومات حديثة."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "📚 الأوامر المتاحة:\n"
            "• أرسل أي سؤال للمحادثة\n"
            "• /draw [وصف الصورة]\n"
            "• /remind [عدد الثواني] [نص التذكير]\n"
            "• /help لعرض هذه القائمة"
        )


async def draw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.message.reply_text("اكتب وصف الصورة بعد الأمر /draw.")
        return
    image_url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
    try:
        await update.message.reply_photo(photo=image_url, caption=prompt[:900])
    except Exception:
        logger.exception("Image generation request failed")
        await update.message.reply_text("تعذّر إنشاء الصورة الآن. حاول مرة أخرى لاحقًا.")


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    try:
        if len(context.args) < 2:
            raise ValueError("الاستخدام الصحيح: /remind [الثواني] [نص التذكير]")
        seconds = int(context.args[0])
        reminder_text = " ".join(context.args[1:]).strip()
        if seconds < 1 or seconds > 30 * 24 * 60 * 60:
            raise ValueError("عدد الثواني يجب أن يكون بين 1 و 2592000.")
        chat_id = update.effective_chat.id

        async def send_reminder():
            if telegram_app:
                await telegram_app.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ تذكير: {reminder_text}",
                )

        scheduler.add_job(
            send_reminder,
            trigger="date",
            run_date=datetime.now() + timedelta(seconds=seconds),
            id=f"reminder_{chat_id}_{datetime.now().timestamp()}",
            replace_existing=False,
        )
        await update.message.reply_text(f"✅ تم جدولة التذكير بعد {seconds} ثانية.")
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {exc}")
    except Exception:
        logger.exception("Reminder scheduling failed")
        await update.message.reply_text("❌ تعذرت جدولة التذكير.")


async def process_ai_response(
    update: Update, user_id: int, message_text: str
) -> None:
    if not update.message or not message_text:
        return
    if groq_client is None:
        await update.message.reply_text(
            "❌ خدمة الذكاء الاصطناعي غير مهيأة. تحقق من متغير GROQ_API_KEY في إعدادات الاستضافة."
        )
        return

    chat_id = update.effective_chat.id
    await update.message.chat.send_action(action="typing")

    history = get_history(user_id, limit=10)
    history.append({"role": "user", "content": message_text})
    save_message(user_id, "user", message_text)

    try:
        max_tool_rounds = 5
        ai_response = None

        for _ in range(max_tool_rounds):
            response = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=history,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=2048,
                temperature=0.4,
            )
            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                ai_response = (assistant_message.content or "").strip()
                break

            history.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            })

            for call in tool_calls:
                tool_name = call.function.name
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                    if not isinstance(arguments, dict):
                        arguments = {}
                except (json.JSONDecodeError, TypeError):
                    arguments = {}

                logger.info("Executing tool: %s", tool_name)
                result = await execute_tool(tool_name, arguments, chat_id)
                history.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": tool_name,
                    "content": str(result)[:12000],
                })

        if not ai_response:
            history.append({
                "role": "system",
                "content": "قدّم أفضل إجابة ممكنة الآن باستخدام نتائج الأدوات الموجودة. لا تستدعِ أدوات إضافية.",
            })
            final_response = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=history,
                tool_choice="none",
                max_tokens=2048,
                temperature=0.4,
            )
            ai_response = (final_response.choices[0].message.content or "").strip()

        if not ai_response:
            ai_response = "ما قدرت أجهّز ردًا هذه المرة. جرّب إعادة صياغة السؤال."

        save_message(user_id, "assistant", ai_response)
        for start_index in range(0, len(ai_response), 4000):
            await update.message.reply_text(ai_response[start_index:start_index + 4000])

    except Exception as exc:
        logger.exception("Error processing AI response")
        error_name = type(exc).__name__
        await update.message.reply_text(
            f"❌ تعذّر إكمال الرد بسبب خطأ تقني ({error_name}). "
            "تحقق من سجلات الاستضافة وإعدادات GROQ_MODEL وGROQ_API_KEY."
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.document:
        return
    document = update.message.document
    user_id = update.effective_user.id
    file_name = document.file_name or "attachment.txt"
    try:
        telegram_file = await document.get_file()
        file_bytes = bytes(await telegram_file.download_as_bytearray())
        if file_name.lower().endswith(".pdf"):
            pages = PdfReader(io.BytesIO(file_bytes)).pages
            extracted = "\n".join(page.extract_text() or "" for page in pages)
        else:
            extracted = file_bytes.decode("utf-8", errors="ignore")
        if not extracted.strip():
            await update.message.reply_text("لم أستطع استخراج نص قابل للقراءة من الملف.")
            return
        await process_ai_response(
            update,
            user_id,
            f"حلّل محتوى الملف المرفق ({file_name}):\n{extracted[:10000]}",
        )
    except Exception:
        logger.exception("Document processing failed")
        await update.message.reply_text("❌ تعذّرت قراءة الملف. تأكد أنه ملف مدعوم وغير تالف.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        return
    if groq_client is None:
        await update.message.reply_text("❌ خدمة الذكاء الاصطناعي غير مهيأة.")
        return
    try:
        voice_file = await update.message.voice.get_file()
        file_bytes = bytes(await voice_file.download_as_bytearray())
        transcription = await groq_client.audio.transcriptions.create(
            file=("voice.ogg", file_bytes),
            model="whisper-large-v3",
        )
        text = (transcription.text or "").strip()
        if not text:
            await update.message.reply_text("لم أستطع فهم التسجيل الصوتي.")
            return
        await process_ai_response(update, update.effective_user.id, text)
    except Exception:
        logger.exception("Voice processing failed")
        await update.message.reply_text("❌ تعذّر تحويل الصوت إلى نص.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    await process_ai_response(
        update,
        update.effective_user.id,
        update.message.text.strip(),
    )


async def telegram_error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    logger.error(
        "Unhandled Telegram error",
        exc_info=context.error,
    )


# ----------------------------- App lifecycle ---------------------------------
async def init_telegram_bot() -> None:
    global telegram_app
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is missing.")
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    try:
        await telegram_app.bot.delete_webhook(drop_pending_updates=False)
    except Exception:
        logger.exception("Could not delete Telegram webhook")

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("draw", draw_command))
    telegram_app.add_handler(CommandHandler("remind", remind_command))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    telegram_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    telegram_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    telegram_app.add_error_handler(telegram_error_handler)

    if not scheduler.running:
        scheduler.start()

    await telegram_app.initialize()
    await telegram_app.start()
    if telegram_app.updater is None:
        raise RuntimeError("Telegram updater is unavailable.")
    await telegram_app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )
    logger.info("Telegram bot polling started.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_telegram_bot()
    try:
        yield
    finally:
        if telegram_app:
            try:
                if telegram_app.updater and telegram_app.updater.running:
                    await telegram_app.updater.stop()
                if telegram_app.running:
                    await telegram_app.stop()
                await telegram_app.shutdown()
            except Exception:
                logger.exception("Error shutting down Telegram bot")
        if scheduler.running:
            scheduler.shutdown(wait=False)


app = FastAPI(title="Stable AI Agent", lifespan=lifespan)


@app.get("/")
async def health_check():
    return JSONResponse({
        "status": "healthy",
        "service": "Stable AI Agent",
        "telegram_configured": bool(TELEGRAM_TOKEN),
        "ai_configured": bool(GROQ_API_KEY),
        "model": GROQ_MODEL,
    })


@app.get("/health")
async def health():
    return {"status": "ok"}


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
