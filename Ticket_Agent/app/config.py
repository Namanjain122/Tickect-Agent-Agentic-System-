# import os
# import logging
# from logging.handlers import TimedRotatingFileHandler
# from dotenv import load_dotenv

# basedir = os.path.abspath(os.path.dirname(__file__))
# load_dotenv(os.path.join(basedir, '../.env'))

# class Config:
#     SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
#     SESSION_SECRET = os.environ.get('SESSION_SECRET') or 'session-secret-change-me'
    
#     # Database configuration
#     DB_DRIVER = os.environ.get('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
#     DB_SERVER = os.environ.get('DB_SERVER', '192.168.1.10')
#     DB_NAME = os.environ.get('DB_NAME', 'ticketdbreport')
#     DB_USER = os.environ.get('DB_USER', 'reportuser')
#     DB_PASSWORD = os.environ.get('DB_PASSWORD', 'sa@123')
    
#     # Groq API configuration
#     GROQ_API_KEY = API_KEY
#     GROQ_MODEL = "llama-3.3-70b-versatile"
    
#     # Application settings
#     OUTPUT_DIR = os.environ.get('OUTPUT_DIR', 'storage/output')
#     MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
#     # Logging configuration - Updated for daily rotation
#     LOG_DIR = os.environ.get("LOG_DIR", os.path.join(basedir, "../logs"))
#     LOG_FILE = os.environ.get("LOG_FILE", "ticket_system.log")
#     ERROR_LOG_FILE = os.environ.get("ERROR_LOG_FILE", "errors.log")
#     LOG_WHEN = os.environ.get("LOG_WHEN", "midnight")  # 'midnight', 'D', 'H', etc.
#     LOG_INTERVAL = int(os.environ.get("LOG_INTERVAL", 1))  # Rotate every interval
#     LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 30))  # Keep 30 days of logs


# class DevelopmentConfig(Config):
#     DEBUG = True


# class ProductionConfig(Config):
#     DEBUG = False


# class TestingConfig(Config):
#     TESTING = True
#     DEBUG = True


# config = {
#     'development': DevelopmentConfig,
#     'production': ProductionConfig,
#     'testing': TestingConfig,
#     'default': DevelopmentConfig
# }


# def setup_logging(app):
#     """
#     Configure logging for Flask app with daily rotation.
#     - INFO+ messages -> ticket_system.log (rotated daily)
#     - ERROR+ messages -> errors.log (rotated daily)
#     """

#     # Ensure log directory exists
#     os.makedirs(app.config['LOG_DIR'], exist_ok=True)

#     # Remove existing handlers to prevent duplicate logging
#     if app.logger.handlers:
#         for handler in app.logger.handlers[:]:
#             app.logger.removeHandler(handler)

#     # Common formatter
#     formatter = logging.Formatter(
#         "%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]"
#     )

#     # Info log handler - Daily rotation
#     info_handler = TimedRotatingFileHandler(
#         filename=os.path.join(app.config['LOG_DIR'], app.config['LOG_FILE']),
#         when=app.config['LOG_WHEN'],
#         interval=app.config['LOG_INTERVAL'],
#         backupCount=app.config['LOG_BACKUP_COUNT'],
#         encoding="utf-8"
#     )
#     info_handler.setLevel(logging.INFO)
#     info_handler.setFormatter(formatter)
#     info_handler.suffix = "%Y-%m-%d"  # Add date suffix to rotated files

#     # Error log handler - Daily rotation
#     error_handler = TimedRotatingFileHandler(
#         filename=os.path.join(app.config['LOG_DIR'], app.config['ERROR_LOG_FILE']),
#         when=app.config['LOG_WHEN'],
#         interval=app.config['LOG_INTERVAL'],
#         backupCount=app.config['LOG_BACKUP_COUNT'],
#         encoding="utf-8"
#     )
#     error_handler.setLevel(logging.ERROR)
#     error_handler.setFormatter(formatter)
#     error_handler.suffix = "%Y-%m-%d"  # Add date suffix to rotated files

#     # Attach handlers
#     app.logger.addHandler(info_handler)
#     app.logger.addHandler(error_handler)

#     # Ensure logging captures both INFO and ERROR
#     app.logger.setLevel(logging.INFO)

#     # Prevent propagation to Flask default logger to avoid duplicates
#     app.logger.propagate = False

#     # Test log
#     app.logger.info("✅ Logging system initialized successfully with daily rotation")
#     app.logger.info(f"Log directory: {app.config['LOG_DIR']}")
#     app.logger.info(f"Log rotation: {app.config['LOG_WHEN']} with {app.config['LOG_BACKUP_COUNT']} days retention")
# app/config.py

import os
from dotenv import load_dotenv
from app.utils.login_config import setup_logging  # ✅ import your logging config

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    SESSION_SECRET = os.environ.get('SESSION_SECRET') or 'session-secret-change-me'
    
    # Database configuration
    DB_DRIVER = os.environ.get('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    DB_SERVER = os.environ.get('DB_SERVER', '192.168.1.10')
    DB_NAME = os.environ.get('DB_NAME', 'ticketdbreport')
    DB_USER = os.environ.get('DB_USER', 'reportuser')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'sa@123')
    
    # Groq API configuration
    GROQ_API_KEY = "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"
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Application settings
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR', 'storage/output')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


# ✅ Call logging setup once when config is loaded
logger = setup_logging()
logger.info("✅ Unified logging initialized via config.py")

