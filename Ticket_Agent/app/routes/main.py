from flask import Blueprint,jsonify
from app.models import database
import os
import traceback
import pandas as pd
import logging
from datetime import datetime

main_bp = Blueprint('main', __name__)

# Configure logging
def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create log filename with timestamp
    log_filename = f"{log_dir}/app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
# Call setup when the blueprint is imported
setup_logging()

@main_bp.route("/", methods=["GET"])
def health():
        logging.info("Health check endpoint accessed")
        try:
            # Example: log database connection status
            db_status = "connected" if database.is_connected() else "disconnected"
            logging.info(f"Database status: {db_status}")
            
            return jsonify({"status": "ok", "model": "ready", "database": db_status}), 200
        except Exception as e:
            logging.error(f"Error in health endpoint: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500