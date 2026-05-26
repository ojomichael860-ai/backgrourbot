import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from rembg import remove
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Web Server for Render Health Checks ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AI Background Remover Engine is Active!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()

# --- Bot Commands and Event Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to the AI Background Remover Bot!**\n\n"
        "Send me any image/photo, and I will use AI to strip away the background "
        "and send you back a clean, transparent PNG file instantly! 🔥",
        parse_mode="Markdown"
    )

async def handle_background_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the image, extracts background using rembg, and returns a PNG document"""
    # Notify user that the AI is processing the image
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_document")
    status_message = await update.message.reply_text("⏳ *AI is processing your image... Please wait.*", parse_mode="Markdown")

    # Define temp working file names
    input_path = f"input_{update.message.message_id}.jpg"
    output_path = f"output_{update.message.message_id}.png"

    try:
        # 1. Download the photo sent by the user (grab highest resolution)
        photo_file = await update.message.photo[-1].get_file()
        await photo_file.download_to_drive(input_path)

        # 2. Run the background isolation process
        input_image = Image.open(input_path)
        output_image = remove(input_image) # rembg Core AI implementation
        output_image.save(output_path, "PNG")

        # 3. Send back the processed image as a high-quality uncompressed Document (to keep transparency)
        with open(output_path, 'rb') as document_out:
            await update.message.reply_document(
                document=document_out,
                filename="no_background.png",
                caption="✅ **Background successfully removed by AI!**"
            )
            
        # Delete the placeholder status text
        await status_message.delete()

    except Exception as e:
        print(f"AI Processing Exception: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred while removing the background from this image.")
    finally:
        # Cleanup file states from the server filesystem
        for temp_file in (input_path, output_path):
            if os.path.exists(temp_file):
                os.remove(temp_file)

async def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Missing TELEGRAM_TOKEN environment target variable.")

    # Run the background port listener for Render
    threading.Thread(target=run_health_server, daemon=True).start()

    # Build the Application framework
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_background_removal))
    
    print("AI Background Isolation Engine starting...")
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
