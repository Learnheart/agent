import os
from dotenv import load_dotenv

load_dotenv()

data_config = {
    "base_url": os.getenv("BASE_URL"),
    "model_name": os.getenv("MODEL_NAME"),
    "api_key": os.getenv("API_KEY")
}