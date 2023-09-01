import os

# Pfade zu Verzeichnissen
FINE_TUNE_DIR = "fine_tune_files"
RAW_DATA_DIR = os.path.join(FINE_TUNE_DIR, "raw_data")
PREPARED_DATA_DIR = os.path.join(FINE_TUNE_DIR, "prepared_data")

# Seps
TRAINING_RAW_DATA_SEPARATOR = "#####"
