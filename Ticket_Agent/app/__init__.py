# import os
# import logging
# from logging.handlers import TimedRotatingFileHandler
# import colorlog
# from datetime import datetime
# from flask import Flask

# def create_app(config_class=None):
#     from flask_login import LoginManager
#     from app.config import Config

#     if config_class is None:
#         config_class = Config

#     app = Flask(__name__)
#     app.config.from_object(config_class)

#     # Initialize login manager
#     login_manager = LoginManager()
#     login_manager.init_app(app)
#     login_manager.login_view = 'auth.login'
#     login_manager.login_message_category = 'info'

#     # Configure user loader
#     from app.models.database import load_user
#     login_manager.user_loader(load_user)

#     # Register blueprints
#     from app.routes.auth import auth_bp
#     # from app.routes.main import main_bp
#     from app.routes.api import api_bp

#     app.register_blueprint(auth_bp)
#     app.register_blueprint(api_bp, url_prefix='/api')
#     # app.register_blueprint(main_bp)
    

#     # ------------------ Logging Setup ------------------

#     basedir = os.path.abspath(os.path.dirname(__file__))
#     log_dir = os.path.join(basedir, "logs")
#     os.makedirs(log_dir, exist_ok=True)

#     # Remove any existing handlers
#     app.logger.handlers.clear()

#     # ------------------ Formatters ------------------
#     # File log formatter
#     file_formatter = logging.Formatter(
#         "%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]"
#     )

#     # Colored console formatter
#     console_formatter = colorlog.ColoredFormatter(
#         "%(log_color)s%(levelname)-8s | %(asctime)s | %(name)s | %(message)s%(reset)s",
#         datefmt='%H:%M:%S',
#         log_colors={
#             'DEBUG': 'cyan',
#             'INFO': 'green',
#             'WARNING': 'yellow',
#             'ERROR': 'red',
#             'CRITICAL': 'red,bg_white',
#         }
#     )

#     # ------------------ Handlers ------------------
#     # Daily rotating log file (INFO+)
#     daily_handler = TimedRotatingFileHandler(
#         os.path.join(log_dir, "ticket_system.log"),
#         when='midnight',
#         interval=1,
#         backupCount=30,
#         encoding="utf-8"
#     )
#     daily_handler.setLevel(logging.INFO)
#     daily_handler.setFormatter(file_formatter)
#     daily_handler.suffix = "%Y-%m-%d"

#     # Daily error log file (ERROR+)
#     error_handler = TimedRotatingFileHandler(
#         os.path.join(log_dir, "errors.log"),
#         when='midnight',
#         interval=1,
#         backupCount=30,
#         encoding="utf-8"
#     )
#     error_handler.setLevel(logging.ERROR)
#     error_handler.setFormatter(file_formatter)
#     error_handler.suffix = "%Y-%m-%d"

#     # Console handler with colors (DEBUG+)
#     console_handler = logging.StreamHandler()
#     console_handler.setLevel(logging.DEBUG)
#     console_handler.setFormatter(console_formatter)

#     # ------------------ Attach Handlers ------------------
#     app.logger.addHandler(daily_handler)
#     app.logger.addHandler(error_handler)
#     app.logger.addHandler(console_handler)

#     # Prevent double logging
#     app.logger.propagate = False

#     # Set overall logger level
#     app.logger.setLevel(logging.DEBUG)

#     # Startup log messages
#     app.logger.info("Ticket Reporting System startup")
#     current_log_file = os.path.join(log_dir, f"ticket_system.log.{datetime.now().strftime('%Y-%m-%d')}")
#     app.logger.info(f"Logging to file: {current_log_file}")

#     # Optional: reduce noisy libraries
#     logging.getLogger('urllib3').setLevel(logging.WARNING)
#     logging.getLogger('werkzeug').setLevel(logging.INFO)

#     return app
import logging
import os
import builtins
from flask import Flask
from flask_login import LoginManager
from app.config import Config
from app.utils.login_config import setup_logging  # ✅ your single log config


def create_app(config_class=None):
    if config_class is None:
        config_class = Config

    app = Flask(__name__)
    app.config.from_object(config_class)

    # ------------------ Login Manager ------------------
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from app.models.database import load_user
    login_manager.user_loader(load_user)

    # ------------------ Register Blueprints ------------------
    from app.routes.auth import auth_bp
    from app.routes.api import api_bp
    # from app.routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    # app.register_blueprint(main_bp)

    # ------------------ Logging Setup ------------------
    setup_logging()  # ✅ creates Logs/app.log.YYYY-MM-DD
    app.logger.handlers = logging.getLogger().handlers  # sync with root logger
    app.logger.setLevel(logging.DEBUG)

    # ------------------ Redirect print() ------------------
    orig_print = builtins.print

    def print_to_logger(*args, **kwargs):
        msg = " ".join(str(arg) for arg in args)
        app.logger.info(msg)
        orig_print(*args, **kwargs)

    builtins.print = print_to_logger

    # ------------------ Startup Logs ------------------
    app.logger.info("✅ Ticket Reporting System startup")
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Logs")
    app.logger.info(f"Logs are written to: {log_dir}/app.log.YYYY-MM-DD")

    # Reduce noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.INFO)

    return app


