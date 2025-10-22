# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv(usecwd=True)
print("Detected .env file:", env_path if env_path else "❌ Not found")

load_dotenv(env_path, override=True)

path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
print("GOOGLE_APPLICATION_CREDENTIALS =", path)
print("File exists:", os.path.exists(path or ""))
