import os
import logging
import asyncio
import re
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, PollAnswerHandler, ContextTypes
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read API keys and temperature from environment
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_TEMPERATURE = 0.85  # Model creativity

if not GOOGLE_API_KEY or not TELEGRAM_TOKEN:
    raise ValueError("Please set GOOGLE_API_KEY and TELEGRAM_TOKEN in .env file")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "\U0001F44B Welcome to the Cucumber + Capybara Quiz Bot!\n\n"
        "Use /quiz to get a new question about Cucumber and Capybara testing.\n"
        "Each question will have three options, and you'll get an explanation for the correct answer."
    )
    await update.message.reply_text(welcome_message)

def generate_quiz_question_sync(max_retries=3):
    prompt = """Generate a multiple-choice question about Cucumber and Capybara testing for freshers. \
    The question should have four options and include a short explanation (one or two sentences) for the correct answer.\
    Each option should be one word or a maximum of three words.\
    Format the response as follows:\
    Question: [question text]\
    Options:\
    A) [option 1]\
    B) [option 2]\
    C) [option 3]\
    D) [option 4]\
    Correct Answer: [letter]\
    Explanation: [explanation]"""

    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                contents=prompt,
                generation_config={"temperature": GEMINI_TEMPERATURE}
            )
            return response.text
        except Exception as e:
            logger.error(f"Error in Gemini API (Attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)
            else:
                return None

async def generate_quiz_question():
    return await asyncio.to_thread(generate_quiz_question_sync)

def parse_quiz_response(response_text):
    try:
        question_match = re.search(r'Question:\s*(.*)', response_text)
        question = question_match.group(1).strip() if question_match else "Question not found"

        options = re.findall(r'(A|B|C|D)\)\s*(.*)', response_text)
        option_list = [text for letter, text in options]

        correct_match = re.search(r'Correct Answer:\s*([A-D])', response_text)
        correct_answer_letter = correct_match.group(1) if correct_match else None
        correct_index = ord(correct_answer_letter) - ord('A') if correct_answer_letter else None

        explanation_match = re.search(r'Explanation:\s*(.*)', response_text, re.DOTALL)
        explanation = explanation_match.group(1).strip() if explanation_match else ''

        return question, option_list, correct_index, explanation

    except Exception as e:
        logger.error(f"Error parsing quiz response: {e}")
        return None, [], None, ''

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response_text = await generate_quiz_question()

    if not response_text:
        await update.message.reply_text("Sorry, failed to generate quiz question. Please try again later.")
        return

    question, options, correct_index, explanation = parse_quiz_response(response_text)

    if correct_index is None or not options:
        await update.message.reply_text("Sorry, could not parse question correctly. Please try again.")
        return

    poll_message = await update.message.reply_poll(
        question=question,
        options=options,
        type="quiz",
        correct_option_id=correct_index,
        is_anonymous=False
    )

    # Save both explanation and chat_id mapped to poll id
    context.bot_data[poll_message.poll.id] = {
        "explanation": explanation,
        "chat_id": update.effective_chat.id
    }

async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_id = update.poll_answer.poll_id
    user = update.effective_user

    data = context.bot_data.get(poll_id)
    if data:
        explanation = data["explanation"]
        chat_id = data["chat_id"]

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📖 Explanation for {user.first_name}:\n{explanation}"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /quiz to get a quiz question.")

async def send_quiz_periodically(application, chat_id, interval_seconds=600):
    while True:
        try:
            # Create a dummy Update and Context for the quiz function
            class DummyMessage:
                async def reply_text(self, text):
                    await application.bot.send_message(chat_id=chat_id, text=text)
                async def reply_poll(self, **kwargs):
                    return await application.bot.send_poll(chat_id=chat_id, **kwargs)
            class DummyUpdate:
                message = DummyMessage()
                effective_chat = type('obj', (object,), {'id': chat_id})()
            class DummyContext:
                bot_data = application.bot_data
            await quiz(DummyUpdate(), DummyContext())
        except Exception as e:
            logger.error(f"Error sending periodic quiz: {e}")
        await asyncio.sleep(interval_seconds)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(PollAnswerHandler(receive_poll_answer))

    # Set your group or user chat_id here for periodic quiz
    PERIODIC_CHAT_ID = None  # e.g., -1001234567890 or your user id
    INTERVAL_SECONDS = 600   # 10 minutes
    if PERIODIC_CHAT_ID:
        application.create_task(send_quiz_periodically(application, PERIODIC_CHAT_ID, INTERVAL_SECONDS))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
