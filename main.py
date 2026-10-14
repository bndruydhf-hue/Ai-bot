import os
import asyncio
import logging
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = "8848083729:AAGfR_NIAmIThDlK5YEggd2ELg66Edtz0Uk"
GROQ_API_KEY = "Gsk_pLGi2K7zq3WfYTK6yMXaWGdyb3FY8Zs7OJsiVWZUZdv1pl5i0pAY"
GROQ_MODEL = "llama-3.3-70b-versatile"
PORT = int(os.environ.get("PORT", 8080))

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

# Global application instance for the Telegram bot
telegram_app: Application = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_message = (
        "🤖 Hello! I'm your AI assistant powered by Groq API.\n\n"
        "Just send me any message and I'll respond using the openai/gpt-oss-120b model.\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/help - Show help information"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help information."""
    help_text = (
        "📚 How to use this bot:\n\n"
        "1. Simply send any text message\n"
        "2. I'll process it through the Groq API using the openai/gpt-oss-120b model\n"
        "3. You'll receive an AI-generated response\n\n"
        "This bot uses the Groq API for fast inference."
    )
    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages and respond using Groq API."""
    user_message = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(f"Received message from {username} (ID: {user_id}): {user_message}")
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        # Call Groq API
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=False
        )
        
        # Extract response
        ai_response = completion.choices[0].message.content
        
        # Send response back to user
        await update.message.reply_text(ai_response)
        logger.info(f"Sent response to {username}")
        
    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        await update.message.reply_text(
            "❌ Sorry, I encountered an error while processing your request. Please try again later."
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")


async def init_telegram_bot():
    """Initialize and start the Telegram bot."""
    global telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    telegram_app.add_error_handler(error_handler)
    
    # Initialize and start the bot
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Telegram bot started successfully")


async def shutdown_telegram_bot():
    """Gracefully shutdown the Telegram bot."""
    global telegram_app
    if telegram_app:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
        logger.info("Telegram bot stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")
    await init_telegram_bot()
    yield
    # Shutdown
    logger.info("Shutting down application...")
    await shutdown_telegram_bot()


# Create FastAPI app with lifespan
app = FastAPI(title="Telegram Bot with Groq API", lifespan=lifespan)


@app.get("/")
async def health_check():
    """Health check endpoint for Render."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "Telegram Bot with Groq API",
            "bot_status": "running" if telegram_app else "not initialized"
        },
        status_code=200
    )


@app.get("/health")
async def health():
    """Alternative health check endpoint."""
    return {"status": "ok"}


def main():
    """Run the FastAPI server with uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")


if __name__ == "__main__":
    main()