import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuroVynx"
    API_V1_STR: str = "/api/v1"
    
    # Storage settings
    DATA_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
    
    # SQLite Configuration
    SQLITE_DB_NAME: str = "eeg_platform.db"
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # SQLite needs an absolute path in the connection string to be safe
        os.makedirs(self.DATA_DIR, exist_ok=True)
        db_path = os.path.join(self.DATA_DIR, self.SQLITE_DB_NAME)
        return f"sqlite:///{db_path}"

settings = Settings()
