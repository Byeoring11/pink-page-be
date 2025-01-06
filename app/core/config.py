import os
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_DIR = os.path.join(BASE_DIR, '.env')


class Config:
    """
    기본 Configuration
    """
    def __init__(self):
        # DB 환경변수
        self.DATABASE_URL: str = os.getenv("DATABASE_URL")

        # HIWARE 환경변수
        self.HIWARE_ID: str = os.getenv("HIWARE_ID")
        self.HIWARE_PW: str = os.getenv("HIWARE_PW")


def get_config():
    load_dotenv(dotenv_path=ENV_DIR)
    return Config()

settings = get_config()
