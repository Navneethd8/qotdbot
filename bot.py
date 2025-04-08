import os
import discord
from discord.ext import commands, tasks
import google.generativeai as genai
from datetime import datetime, time
import zoneinfo
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('question-bot')

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
QUESTION_CHANNEL_ID = int(os.getenv('QUESTION_CHANNEL_ID', '0')) 
QUESTION_HOUR = int(os.getenv('QUESTION_HOUR', '17'))  
QUESTION_MINUTE = int(os.getenv('QUESTION_MINUTE', '00')) 


PACIFIC_TZ = zoneinfo.ZoneInfo("America/Los_Angeles")
scheduled_time = time(hour=QUESTION_HOUR, minute=QUESTION_MINUTE, tzinfo=PACIFIC_TZ)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

async def generate_question():
    """Generate a question using Gemini Flash API"""
    try:
        prompt = """ 
        Generate a thought-provoking question of the day that will spark interesting discussions. 
        The question should be open-ended and suitable for a diverse audience. 
        It is more helopful if the questions are food related
        Only return the question itself without any additional text.
        Do not repeat questions.
        """
        
        response = await asyncio.to_thread(
            lambda: model.generate_content(prompt)
        )
        
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating question: {e}")
        return "What's something you've learned recently that surprised you?"  # Fallback question

    
@tasks.loop(time=scheduled_time)
async def post_question_of_the_day():
    """Post the question of the day at the scheduled time"""
    try:
        logger.info(f"Task triggered at {datetime.now()}")
        channel = bot.get_channel(int(os.getenv('QUESTION_CHANNEL_ID', '0')))
        if not channel:
            logger.error(f"Channel with ID {QUESTION_CHANNEL_ID} not found")
            return
            
        question = await generate_question()

        message = f"**@here**\n\n**✨Question of the Day✨**\n\n{question}\n\n"
        
        await channel.send(message)

        
        logger.info(f"Posted question of the day: {question}")
    except Exception as e:
        logger.error(f"Error posting question: {e}")

@post_question_of_the_day.before_loop
async def before_post_question():
    """Wait until the bot is ready before starting the task"""
    await bot.wait_until_ready()
    logger.info("Question of the day task is ready")

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f"Logged in as {bot.user.name}")
    post_question_of_the_day.start()

@bot.command(name="qotd")
@commands.has_permissions(administrator=True)
async def manual_question(ctx):
    """Manually trigger a question of the day"""
    question = await generate_question()
    
    message = f"**@here**\n\n**✨Question of the Day✨**\n\n{question}\n\n"
    
    await ctx.send(message)
    
    logger.info(f"Manually posted question: {question}")

# Run the bot
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN environment variable not set")
        exit(1)
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY environment variable not set")
        exit(1)
    if QUESTION_CHANNEL_ID == 0:
        logger.warning("QUESTION_CHANNEL_ID not set. Please set it to post questions automatically.")
    
    logger.info("Starting bot...")
    bot.run(DISCORD_TOKEN)
