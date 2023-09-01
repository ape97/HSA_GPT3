import openai
from dotenv import load_dotenv
from utils import LogLevel, custom_print, create_directory, print_header
from gpt import list_fine_tuned_models, create_fine_tuned_model, delete_fine_tuned_model, get_openai_key, create_training_file, train_model, merge_training_files, read_and_prepare_data
from config import FINE_TUNE_DIR, RAW_DATA_DIR, PREPARED_DATA_DIR

def exit_program():
    custom_print("Auf Wiedersehen!", LogLevel.INFO)
    exit()

def create_required_directories():
    for directory in [FINE_TUNE_DIR, RAW_DATA_DIR, PREPARED_DATA_DIR]:
        create_directory(directory)

def show_main_menu():
    menu = {
        "1": "Trainingsdatei (.jsonl) erstellen",
        "2": "Fine-tuning-Modell trainieren",
        "3": "Trainingsdateien (.jsonl) zusammenführen",
        "4": "Fine-Tuning-Modelle auflisten",
        "5": "Fine-Tuning-Modell erstellen",
        "6": "Fine-Tuning-Modell löschen",
        "7": "Vorbereitete Fragen und Antworten verwenden (Frage: Antwort:)",
        "q": "Beenden"
    }

    blue_color = "\033[94m"
    reset_color = "\033[0m"

    print_header("Hauptmenü - Bitte wählen Sie eine der folgenden Optionen:")

    for key, value in menu.items():
        print(f"{blue_color}{key}. {value}{reset_color}")

    choice = input(
        "\nBitte geben Sie die gewünschte Option ein: ").lower()

    return choice

def main():
    function_mappings = {
        "1": create_training_file,
        "2": train_model,
        "3": merge_training_files,
        "4": list_fine_tuned_models,
        "5": create_fine_tuned_model,
        "6": delete_fine_tuned_model,
        "7": read_and_prepare_data,
        "q": exit_program
    }

    try:
        create_required_directories()
    except OSError as e:
        custom_print(
            f"Fehler beim Erstellen eines Verzeichnisses: {e}", LogLevel.ERROR)
        exit(1)

    load_dotenv()
    openai.api_key = get_openai_key()

    while True:
        choice = show_main_menu()
        selected_function = function_mappings.get(choice)

        if selected_function:
            selected_function()
        else:
            custom_print("Ungültige Eingabe!", LogLevel.ERROR)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        custom_print(
            f"Ein unerwarteter Fehler ist aufgetreten: {e}", LogLevel.ERROR)
