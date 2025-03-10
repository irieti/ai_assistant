import time
import telebot
from ai_assistant.openai_service import AIAssistant
from ai_assistant.views import get_chat_mapping, update_chat_mapping
import os
from openai import OpenAI
import logging

# Set up logging for debugging purposes
logger = logging.getLogger(__name__)

client = OpenAI()
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
ai_assistant = AIAssistant(api_key=os.getenv("OPENAI_API_KEY"))


@bot.message_handler(commands=["start"])
def send_welcome(message):
    """Handles the /start command by initializing the chat thread."""
    print("Received /start command.")

    bot.reply_to(message, "Hey, I'm your AI Assistant, tell me your question?")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Processes user messages and interacts with the AI assistant."""
    print(f"Received user message: {message.text}")
    chat_id = message.chat.id
    user_input = message.text

    # Notify the user that the assistant is processing the request
    processing_msg = bot.send_message(chat_id, "🤖 Thinking...")
    print(f"Sent 'thinking' message: {processing_msg.message_id}")

    # Call the AIAssistant's get_response method
    print(f"Sending user input to assistant: {user_input}")
    response = ai_assistant.get_response(
        integration="telegram", chat_id=chat_id, prompt=user_input
    )

    if response:
        print(f"Sending assistant response: {response}")
        bot.send_message(
            chat_id,
            response.value,
        )
    else:
        print("Sending error message: Unable to retrieve response from AI.")
        bot.send_message(
            chat_id,
            "Error: Could not get a response from AI.",
        )

    # Delete the 'thinking' message
    print(f"Deleting 'thinking' message with ID: {processing_msg.message_id}")
    bot.delete_message(chat_id, processing_msg.message_id)


def run():
    """Runs the Telegram bot."""
    print("Telegram bot is running...")
    bot.polling(none_stop=True)
