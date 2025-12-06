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
    # 데이터베이스 설정
    db: DatabaseSettings = DatabaseSettings()

    # 환경 설정
    ENV: str = Field(..., pattern="^(development|staging|production)$")

    # 기본 애플리케이션 설정
    APP_NAME: str = "Pink-Page API Server"
    APP_DESC: str = "This is a pink-page API server developed with FastAPI"
    APP_VERSION: str = "0.0.1"
    DOCS_URL: Optional[str] = "/swagger/docs"
    DEBUG: bool = True

    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"

    # 하이웨어 설정
    HIWARE_ID: str = Field(...)
    HIWARE_PW: str = Field(...)
    MDWAP1P_IP: str = Field(...)
    MYPAP1D_IP: str = Field(...)

    # 환경별 설정값 조정
    def configure_for_environment(self):
        if self.ENV == "production":
            self.DEBUG = False
            self.DOCS_URL = None
        elif self.ENV == "development":
            self.DEBUG = True
            self.LOG_LEVEL = "DEBUG"

    # 환경변수 파일 설정
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore'
    )


settings = Settings()
settings.configure_for_environment()
