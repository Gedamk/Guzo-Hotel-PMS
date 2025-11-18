import os
from dotenv import load_dotenv

env_path = r"C:\Users\Gedan\Desktop\Guzo\.env"
load_dotenv(dotenv_path=env_path)

print("Testing .env load from:", env_path)
print("SENDGRID_API_KEY:", os.getenv("SENDGRID_API_KEY"))
