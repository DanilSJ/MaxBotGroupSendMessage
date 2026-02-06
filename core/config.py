from os import getenv

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    TOKEN: str = getenv('TOKEN')
    CONFIG_FILE: str = "config.json"

settings = Settings()