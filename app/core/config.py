from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional
from pydantic import Field


class DatabaseSettings(BaseSettings):
    # 프로젝트 루트 디렉토리 설정
    BASE_DIR: Path = Path(__file__).parent.parent.parent

    # 데이터베이스 관련 설정
    DB_FOLDER: str = "data"
    DB_NAME: str = "sqlite.db"

    @property
    def DB_DIR(self) -> Path:
        """데이터베이스 저장 디렉토리"""
        db_dir = self.BASE_DIR / self.DB_FOLDER
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir

    @property
    def DB_PATH(self) -> Path:
        """데이터베이스 파일 전체 경로"""
        return self.DB_DIR / self.DB_NAME

    @property
    def DATABASE_URL(self) -> str:
        """SQLAlchemy 연결 URL"""
        return f"sqlite+aiosqlite:///{self.DB_PATH}"


class Settings(BaseSettings):
    # 기본 애플리케이션 설정
    APP_NAME: str = "Pink-Page API Server"
    APP_DESC: str = "This is a pink-page API server developed with FastAPI"
    APP_VERSION: str = "0.0.1"
    DEBUG: bool = True

    # 환경 설정
    ENV: str = Field("development", pattern="^(development|staging|production)$")

    # API 설정
    API_PREFIX: str = "/api"
    API_V1_PREFIX: str = "/v1"
    DOCS_URL: Optional[str] = "/docs"

    # 데이터베이스 설정
    db: DatabaseSettings = DatabaseSettings()

    # 하이웨어 설정
    HIWARE_ID: str = Field(...)
    HIWARE_PW: str = Field(...)
    WDEXGM1P_IP: str = Field(..., env="WDEXGM1P_IP")
    EDWAP1T_IP: str = Field(..., env="EDWAP1T_IP")
    MYPAP1D_IP: str = Field(..., env="MYPAP1D_IP")
    SERVERS: list[str] = []

    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 환경변수 파일 설정
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore'
    )

    # 환경별 설정값 조정
    def configure_for_environment(self):
        if self.ENV == "production":
            self.DEBUG = False
            self.DOCS_URL = None
        elif self.ENV == "development":
            self.DEBUG = True
            self.LOG_LEVEL = "DEBUG"


settings = Settings()
settings.configure_for_environment()
settings.SERVERS = ['', settings.WDEXGM1P_IP, settings.EDWAP1T_IP, settings.MYPAP1D_IP]
