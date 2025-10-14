import logging
logging.basicConfig(
    format="%(asctime)s - GuzoBot - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
