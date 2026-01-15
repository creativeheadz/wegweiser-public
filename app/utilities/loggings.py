# Filepath: app/utilities/loggings.py
import logging

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
        logging.FileHandler("faiss_ollama_summary.log"),
        logging.StreamHandler()
    ])
    return logging.getLogger(__name__)


logger = setup_logging()

