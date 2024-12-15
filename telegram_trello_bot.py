import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramTrelloBotManager:
    def __init__(self, telegram_token, trello_api_key, trello_token, trello_board_id):
        """
        Initialize bot with credentials
        
        :param telegram_token: Token from BotFather
        :param trello_api_key: Trello API Key
        :param trello_token: Trello Authorization Token
        :param trello_board_id: Trello Board to interact with
        """
        # Store credentials securely
        self.telegram_token = telegram_token
        self.trello_api_key = trello_api_key
        self.trello_token = trello_token
        self.trello_board_id = trello_board_id
        
        # Trello API base URL for requests
        self.trello_base_url = "https://api.trello.com/1"
        
        # Default list name for creating cards
        self.default_list_name = "Todo"
        
        logger.info("TelegramTrelloBotManager initialized")
    
    def create_trello_card(self, list_id: str, card_name: str, description: str = "") -> dict:
        """
        Create a card in a specific Trello list
        
        :param list_id: Trello list to add card to
        :param card_name: Title of the card
        :param description: Optional card description
        :return: Trello API response
        """
        url = f"{self.trello_base_url}/cards"
        params = {
            "key": self.trello_api_key,
            "token": self.trello_token,
            "idList": list_id,
            "name": card_name,
            "desc": description
        }
        
        # Send POST request to Trello
        response = requests.post(url, params=params)
        return response.json()
    
    def get_trello_lists(self) -> list:
        """
        Retrieve lists from the specified Trello board
        
        :return: List of board lists
        """
        url = f"{self.trello_base_url}/boards/{self.trello_board_id}/lists"
        params = {
            "key": self.trello_api_key,
            "token": self.trello_token
        }
        
        # Send GET request to Trello
        response = requests.get(url, params=params)
        return response.json()
    
    async def telegram_create_card_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /createcard command in Telegram
        
        Usage: /createcard List_Name Card Title
        """
        logger.info(f"Create card command received from {update.effective_user.username}")
        
        # Check if correct number of arguments provided
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /createcard <list_name> <card_title>\n"
                "Example: /createcard Todo 'Buy groceries'"
            )
            return
        
        # Separate list name and card title
        list_name = context.args[0]
        card_title = " ".join(context.args[1:])
        
        # Get board lists
        try:
            lists = self.get_trello_lists()
            logger.info(f"Retrieved {len(lists)} Trello lists")
        except Exception as e:
            logger.error(f"Error retrieving Trello lists: {e}")
            await update.message.reply_text(f"Error retrieving Trello lists: {e}")
            return
        
        # Find matching list
        matching_list = next((lst for lst in lists if lst['name'].lower() == list_name.lower()), None)
        
        if not matching_list:
            await update.message.reply_text(f"No list found with name: {list_name}")
            return
        
        # Create card
        try:
            card = self.create_trello_card(matching_list['id'], card_title)
            await update.message.reply_text(f"Card '{card_title}' created in list '{list_name}'!")
        except Exception as e:
            logger.error(f"Error creating Trello card: {e}")
            await update.message.reply_text(f"Error creating card: {str(e)}")
    
    async def telegram_trello_reply_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /trello command when replying to a message
        Creates a card in the default Todo list with the replied message text
        """
        logger.info(f"/trello command received from {update.effective_user.username}")
        
        # Check if this is a reply to another message
        if not update.message.reply_to_message:
            await update.message.reply_text("Please use /trello as a reply to a message you want to create a Trello card for.")
            return
        
        # Get the text of the original message
        original_message = update.message.reply_to_message.text or update.message.reply_to_message.caption
        
        if not original_message:
            await update.message.reply_text("The message you replied to doesn't contain any text.")
            return
        
        # Get board lists
        try:
            lists = self.get_trello_lists()
            logger.info(f"Retrieved {len(lists)} Trello lists")
        except Exception as e:
            logger.error(f"Error retrieving Trello lists: {e}")
            await update.message.reply_text(f"Error retrieving Trello lists: {e}")
            return
        
        # Find the Todo list
        todo_list = next((lst for lst in lists if lst['name'].lower() == self.default_list_name.lower()), None)
        
        if not todo_list:
            await update.message.reply_text(f"No '{self.default_list_name}' list found in the board.")
            return
        
        # Create card
        try:
            # Truncate long messages to ensure card name isn't too long
            card_name = original_message[:150] + '...' if len(original_message) > 150 else original_message
            card = self.create_trello_card(todo_list['id'], card_name)
            await update.message.reply_text(f"Card created in {self.default_list_name} list!")
        except Exception as e:
            logger.error(f"Error creating Trello card: {e}")
            await update.message.reply_text(f"Error creating card: {str(e)}")
    
    async def send_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Send a welcome message when the /start command is issued
        """
        logger.info(f"Welcome message sent to {update.effective_user.username}")
        welcome_message = (
            "Welcome to the Trello Card Creator Bot! 🤖\n\n"
            "Commands:\n"
            "- /createcard <list_name> <card_title>: Create a card in a specific list\n"
            "- Reply to any message with /trello to create a card in the Todo list"
        )
        await update.message.reply_text(welcome_message)

def main():
    # Retrieve credentials from environment variables
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TRELLO_API_KEY = os.getenv('TRELLO_API_KEY')
    TRELLO_TOKEN = os.getenv('TRELLO_TOKEN')
    TRELLO_BOARD_ID = os.getenv('TRELLO_BOARD_ID')
    
    # Validate all credentials are set
    if not all([TELEGRAM_TOKEN, TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID]):
        logger.error("Missing one or more required environment variables")
        print("Please set all required environment variables:")
        print("- TELEGRAM_BOT_TOKEN")
        print("- TRELLO_API_KEY")
        print("- TRELLO_TOKEN")
        print("- TRELLO_BOARD_ID")
        return
    
    try:
        # Initialize bot manager
        bot_manager = TelegramTrelloBotManager(
            TELEGRAM_TOKEN, 
            TRELLO_API_KEY, 
            TRELLO_TOKEN, 
            TRELLO_BOARD_ID
        )
        
        # Create the Application and pass it your bot's token
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot_manager.send_welcome))
        application.add_handler(CommandHandler("createcard", bot_manager.telegram_create_card_command))
        application.add_handler(CommandHandler("trello", bot_manager.telegram_trello_reply_command))
        
        # Start the bot
        logger.info("Attempting to start bot polling")
        print("Starting bot polling...")
        application.run_polling(drop_pending_updates=True)
        logger.info("Bot polling started successfully")
    
    except Exception as e:
        logger.error(f"An error occurred while starting the bot: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()