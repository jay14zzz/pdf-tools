import os

class Config:
    # Basic Flask Settings
    SECRET_KEY = os.urandom(24)  # For session management
    DEBUG = False

    # Upload Settings
    UPLOAD_FOLDER = 'uploads'      # Default local folder for uploads
    RESULT_FOLDER = 'results'      # Folder for processed results
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size

class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
