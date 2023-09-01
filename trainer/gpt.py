import openai
import os
import json
import datetime
import subprocess
from dotenv import load_dotenv
from config import RAW_DATA_DIR, PREPARED_DATA_DIR, TRAINING_RAW_DATA_SEPARATOR
from utils import LogLevel, custom_print, print_header, custom_input


def get_user_confirmation(message):
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    response = input(
        f"{YELLOW}{message} [j/n]: {RESET}").lower()
    return response == 'j'


def get_user_choice(message, min_value, max_value):
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    while True:
        try:
            choice = int(input(f"{YELLOW}{message}{RESET}"))
            if min_value <= choice <= max_value:
                return choice
            else:
                custom_print("Ungültige Auswahl.", LogLevel.ERROR)
        except ValueError:
            custom_print(
                "Bitte geben Sie eine gültige Nummer ein.", LogLevel.ERROR)


def open_terminal_with_command(command, env_vars=None):
    if os.name == 'nt':  # Windows
        cmd = ['cmd.exe', '/c', 'start', 'cmd.exe', '/k', command]
    else:  # macOS and Linux
        cmd = ['x-terminal-emulator', '-e', command]

    if env_vars:
        env = os.environ.copy()
        env.update(env_vars)
    else:
        env = None

    subprocess.Popen(cmd, env=env)


def get_openai_key():
    try:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API-Schlüssel nicht gefunden.")
        return api_key
    except Exception as e:
        custom_print(
            f"Ein unerwarteter Fehler ist aufgetreten: {e}", LogLevel.ERROR)
        raise e


def handle_openai_errors(func):
    # https://platform.openai.com/docs/guides/error-codes/python-library-error-types
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except openai.error.APIError as e:
            custom_print(
                f"OpenAI API returned an API Error: {e}", LogLevel.ERROR)
        except openai.error.APIConnectionError as e:
            custom_print(
                f"Failed to connect to OpenAI API: {e}"), LogLevel.ERROR
        except openai.error.RateLimitError as e:
            custom_print(
                f"OpenAI API request exceeded rate limit: {e}", LogLevel.ERROR)
        except Exception as e:
            custom_print(f"Allgemeiner Fehler: {e}", LogLevel.ERROR)

    return wrapper


def merge_training_files():
    # Diese Funktion führt mehrere Trainingsdateien zusammen

    print_header("Zusammenführung von Trainingsdateien (.jsonl)")

    selected_files = []

    while True:
        # Dateien auflisten
        all_files = [f for f in os.listdir(
            PREPARED_DATA_DIR) if f.endswith('.jsonl')]
        available_files = [f for f in all_files if f not in selected_files]

        # Abbrechen, wenn keine Dateien mehr vorhanden sind
        if not available_files:
            custom_print("Keine weiteren Dateien vorhanden.", LogLevel.INFO)
            break

        custom_print("\nVerfügbare Dateien:", LogLevel.INFO)
        for idx, filename in enumerate(available_files, 1):
            print(f"{idx}. {filename}")

        # Datei auswählen
        try:
            choice = get_user_choice(
                "\nWählen Sie eine Datei durch Eingabe der Nummer: ", 1, len(available_files))
            if choice is not None:
                selected_file = available_files[choice - 1]
                selected_files.append(selected_file)
            else:
                custom_print("Ungültige Auswahl.", LogLevel.ERROR)
                continue
        except ValueError:
            custom_print(
                "Bitte geben Sie eine gültige Nummer ein.", LogLevel.ERROR)
            continue

        # Weiter wählen oder abbrechen
        if not get_user_confirmation(
                "Wollen Sie eine weitere Datei hinzufügen?"):
            break

    # Bestätigung zum Mergen
    if not get_user_confirmation("Möchten Sie die ausgewählten Dateien zusammenführen?"):
        custom_print("Zusammenführung abgebrochen.", LogLevel.INFO)
        return

    # Inhalte der Dateien zusammenführen
    merged_data = []
    for file in selected_files:
        with open(os.path.join(PREPARED_DATA_DIR, file), 'r', encoding='utf-8') as f:
            merged_data.extend([json.loads(line) for line in f])

    # Inhalte anzeigen
    custom_print("\nZusammengeführte Daten:", LogLevel.INFO)
    for item in merged_data:
        print(json.dumps(item))

    # Bestätigung zum Speichern
    if get_user_confirmation("Ist die Zusammenführung korrekt und soll gespeichert werden?"):
        filename = input(
            "\nBitte geben Sie den gewünschten Dateinamen ohne Erweiterung ein: ") + ".jsonl"
        with open(os.path.join(PREPARED_DATA_DIR, filename), 'w', encoding='utf-8') as f:
            for item in merged_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        custom_print(
            f"\nDaten wurden in {filename} gespeichert.", LogLevel.INFO)

    # Bestätigung zum Löschen der alten Dateien
    if get_user_confirmation("Möchten Sie die ursprünglichen Dateien löschen?"):
        for file in selected_files:
            os.remove(os.path.join(PREPARED_DATA_DIR, file))
        custom_print(
            "\nDie ausgewählten Dateien wurden gelöscht.", LogLevel.INFO)

    custom_print("\nDie Zusammenführung ist abgeschlossen."), LogLevel.INFO


@handle_openai_errors
def train_model():
    # Diese Funktion startet das Training (fine-tune)

    print_header("GPT-3 Fine-Tune (Modell trainieren)")

    openai.api_key = get_openai_key()
    models = openai.FineTune.list()

    list_fine_tuned_models()

    if not models or not models.data:
        custom_print(
            "Es wurden keine Fine-Tuning-Modelle gefunden.", LogLevel.INFO)
        return

    model_choice = get_user_choice(
        "\nBitte wählen Sie ein vorhandenes Modell zur Weiterverfeinerung:", 1, len(models.data))
    chosen_model = models.data[model_choice - 1].fine_tuned_model

    custom_print("\nWählen Sie, wie Sie die Trainingsdatei angeben möchten:")
    custom_print("[1] Eigenen Pfad eingeben")
    custom_print("[2] Aus vorhandenen Dateien wählen")

    file_select_method = get_user_choice("Option auswählen:", 1, 2)

    if file_select_method == 1:
        training_file = custom_input(
            "\nBitte geben Sie den vollständigen Pfad zur Trainingsdatei ein: ")
    elif file_select_method == 2:
        files = [f for f in os.listdir(
            PREPARED_DATA_DIR) if f.endswith('.jsonl')]
        for idx, file in enumerate(files, 1):
            print(f"{idx}. {file}")

        file_choice = get_user_choice(
            "\nBitte wählen Sie die Trainingsdatei durch Eingabe der entsprechenden Zahl:", 1, len(files))
        training_file = os.path.join(PREPARED_DATA_DIR, files[file_choice - 1])
    else:
        custom_print("Ungültige Auswahlmethode.", LogLevel.ERROR)
        return

    if get_user_confirmation(f"Fine-Tuning für Modell '{chosen_model}' mit der Datei '{training_file}' starten?"):
        command = f"openai api fine_tunes.create -t {training_file} -m {chosen_model}"
        open_terminal_with_command(command)
        custom_print("\nDer Fine-Tuning-Prozess wurde in einem neuen Fenster gestartet. Bitte überprüfen Sie dieses Fenster, um den Fortschritt zu verfolgen.", LogLevel.INFO)
    else:
        custom_print("\nFine-Tuning wurde abgebrochen.", LogLevel.INFO)


@handle_openai_errors
def list_fine_tuned_models():

    print_header("Auflistung aller Fine-Tune Modelle")

    openai.api_key = get_openai_key()

    models = openai.FineTune.list()

    if models and models.data:
        print("Fine-Tuning-Modelle:")
        print("\n")
        for index, model in enumerate(models.data, start=1):
            custom_print(f"   Nr.: {index}")
            print(f"   Bezeichnung: {model.fine_tuned_model}")
            print(f"   Modell: {model.model}")
            print(f"   ID: {model.id}")
            print(f"   Status: {model.status}")
            print(
                f"   Erstellt am: {datetime.datetime.fromtimestamp(model.created_at)}")
            print(
                f"   Aktualisiert am: {datetime.datetime.fromtimestamp(model.updated_at)}")
            print(f"   Organization ID: {model.organization_id}")
            print("\n")
        print("\n")
    else:
        print("Keine Fine-Tuning-Modelle gefunden.")


@handle_openai_errors
def create_fine_tuned_model():
    print_header("Erstellung eines neuen Fine-Tuning-Modells")

    base_models = ["ada", "babbage", "curie", "davinci"]
    for idx, model in enumerate(base_models, 1):
        print(f"{idx}. {model}")

    model_choice = get_user_choice(
        "\nBitte wählen Sie das Basis-Modell:", 1, 4)
    chosen_model = base_models[model_choice - 1]

    custom_print("\nWählen Sie, wie Sie die Trainingsdatei angeben möchten:")
    custom_print("1. Eigenen Pfad eingeben")
    custom_print("2. Aus vorhandenen Dateien wählen")

    file_select_method = get_user_choice("Option auswählen:", 1, 2)

    if file_select_method == 1:
        training_file = custom_input(
            "\nBitte geben Sie den vollständigen Pfad zur Trainingsdatei ein: ")
    elif file_select_method == 2:
        files = [f for f in os.listdir(
            PREPARED_DATA_DIR) if f.endswith('.jsonl')]
        for idx, file in enumerate(files, 1):
            print(f"{idx}. {file}")

        file_choice = get_user_choice(
            "\nBitte wählen Sie die Trainingsdatei durch Eingabe der entsprechenden Zahl:", 1, len(files))
        training_file = os.path.join(PREPARED_DATA_DIR, files[file_choice - 1])
    else:
        custom_print("Ungültige Auswahlmethode.", LogLevel.ERROR)
        return

    suffix = custom_input("Geben Sie einen Suffix für Ihr Modell ein: ")

    if get_user_confirmation(f"Fine-Tuning für Modell '{chosen_model}' mit der Datei '{training_file}' und Suffix '{suffix}' starten?"):
        command = f"openai api fine_tunes.create -t {training_file} -m {chosen_model} --suffix {suffix}"

        open_terminal_with_command(
            command, env_vars={"OPENAI_KEY": openai.api_key})

        custom_print("\nDer Fine-Tuning-Prozess wurde in einem neuen Fenster gestartet. Bitte überprüfen Sie dieses Fenster, um den Fortschritt zu verfolgen.", LogLevel.INFO)


@handle_openai_errors
def delete_fine_tuned_model():
    print_header("Löschung eines bestehenden Fine-Tuning-Modells")

    openai.api_key = get_openai_key()
    models = openai.FineTune.list()

    list_fine_tuned_models()

    if models and models.data:
        index_input = custom_input(
            "Geben Sie die Nr. des zu löschenden Modells ein: ")
        if index_input.isdigit():
            index = int(index_input)
            if index >= 1 and index <= len(models.data):
                model_to_delete = models.data[index - 1]

                if get_user_confirmation(f"Sicherheitsfrage: Möchten Sie Modell Nr. {index} wirklich löschen?"):
                    openai.Model.delete(model_to_delete.fine_tuned_model)
                    custom_print(
                        f"Modell Nr. {index} erfolgreich gelöscht.", LogLevel.INFO)
                else:
                    custom_print("Löschung abgebrochen.", LogLevel.INFO)
            else:
                custom_print(
                    "Ungültige Nr. Das Modell existiert nicht.", LogLevel.ERROR)
        else:
            custom_print(
                "Ungültige Eingabe. Bitte geben Sie eine Zahl ein.", LogLevel.ERROR)
    else:
        custom_print("Keine Fine-Tuning-Modelle gefunden.", LogLevel.INFO)


@handle_openai_errors
def create_training_file():
    print_header("Erstellung einer Trainingsdatei (fine-tune .jsonl)")

    ############################################
    # Schritt 1: Benutzerinformationen
    print("\nErstellungsprozess für Trainingsdatei (.jsonl):")
    custom_print(
        "Hier sind einige grundlegende Informationen und Anforderungen:")
    custom_print("- Ihre Daten sollten im .txt-Format vorliegen.")
    custom_print(
        f"- Verwenden Sie das Trennzeichen '{TRAINING_RAW_DATA_SEPARATOR}', um verschiedene Abschnitte/Bereiche in Ihrer Datei zu trennen.")

    ############################################
    # Schritt 2: Dateipfad-Eingabe
    raw_data_filename = ""  # Wird in Schritt 6 verwendet
    choice = get_user_choice(
        "\nMöchten Sie eine Datei aus dem definierten Verzeichnis '" + RAW_DATA_DIR + "' wählen [1] oder den absoluten Pfad einer .txt-Datei angeben [2]?", 1, 2)

    if choice == 2:
        # Absoluter Pfad
        file_path = custom_input(
            "Bitte geben Sie den absoluten Pfad Ihrer .txt-Datei an: ")
        raw_data_filename = os.path.splitext(os.path.basename(file_path))[0]

    elif choice == 1:
       # Definiertes Verzeichnis
        files = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith(".txt")]
        if not files:
            custom_print(
                "Keine .txt-Dateien im definierten Verzeichnis gefunden.", LogLevel.ERROR)
            return

        print("\nListe der verfügbaren .txt-Dateien:")
        for idx, file in enumerate(files, 1):
            print(f"{idx}. {file}")

        choice = get_user_choice(
            "\nBitte wählen Sie die Nummer der Datei, die Sie verwenden möchten: ", 1, len(
                files)
        )
        file_path = os.path.join(RAW_DATA_DIR, files[choice - 1])
        raw_data_filename = os.path.splitext(files[choice - 1])[0]
    else:
        custom_print("Ungültige Asuwahl.", LogLevel.ERROR)
        return

    ############################################
    # Schritt 3: Datei lesen und in Abschnitte aufteilen
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            sections = content.split(TRAINING_RAW_DATA_SEPARATOR)
            sections = [section.strip()
                        for section in sections if section.strip()]

        custom_print(
            f"\n{len(sections)} Abschnitte wurden aus der Datei extrahiert.", LogLevel.INFO)

        # Benutzerverifikation der extrahierten Abschnitte
        custom_print("\n--- Start der Abschnitte ---")
        for idx, section in enumerate(sections, 1):
            print(f"Abschnitt {idx}:\n{section}\n")
        custom_print("--- Ende der Abschnitte ---")

        if not get_user_confirmation(f"Bestätigen Sie die Richtigkeit dieser Abschnitte?"):
            custom_print(
                "Von Benutzer abgebrochen. Rückkehr zum Menü.", LogLevel.INFO)
            return

    except FileNotFoundError:
        custom_print(f"Datei '{file_path}' nicht gefunden.", LogLevel.ERROR)
    except Exception as e:
        custom_print(f"Fehler beim Lesen der Datei: {e}", LogLevel.ERROR)

    ############################################
    # Schritt 4: Arbeit mit bestätigten Abschnitten
    # Nachdem der Benutzer Abschnitte in Schritt 3 bestätigt hat
    if get_user_confirmation("\nMöchten Sie die Abschnitte optimieren, um unnötige Zeichen zu entfernen?"):
        for idx, section in enumerate(sections):
            # Entfernen von unnötigen Leerzeichen, Tabs und doppelten Zeilenumbrüchen
            section = section.replace("\t", " ")
            section = ' '.join(section.split())
            section = "\n".join(line.strip()
                                for line in section.splitlines() if line.strip())
            sections[idx] = section

        print("\nOptimierte Abschnitte:")
        custom_print("\n--- Start der optimierten Abschnitte ---")
        for idx, section in enumerate(sections, 1):
            print(f"Abschnitt {idx}:\n{section}\n")
        custom_print("--- Ende der optimierten Abschnitte ---")

        if not get_user_confirmation("Bestätigen Sie die Richtigkeit dieser optimierten Abschnitte?"):
            custom_print(
                "Optimierung vom Benutzer abgebrochen. Rückkehr zum Menü.", LogLevel.INFO)
            return

    ############################################
    # Schritt 5: ChatGPT Frage-/Antwortgenerierung

    if not get_user_confirmation("\nMöchten Sie den Prozess zur Generierung von Fragen und Antworten mithilfe von GPT (Modell: text-davinci-003) starten? Dies kann einige Zeit dauern und ist mit Kosten verbunden."):
        custom_print(
            "Generierung vom Benutzer abgebrochen. Rückkehr zum Menü.", LogLevel.INFO)
        return

    custom_print(
        "\nDie Generierung wurde gestartet. Dies kann eine Weile dauern...\n", LogLevel.INFO)

    ######################## Statische Antworten für Debug-Zwecke:
    # static_responses = {
    #     1: "Frage: Welchen Zweck erfüllt die Talsperre Valdeobispo? Antwort: Die Talsperre Valdeobispo dient der Stromerzeugung und der Bewässerung.Frage: Welcher Fluss staut die Talsperre Valdeobispo auf? Antwort: Die Talsperre Valdeobispo staut den Alagón auf.Frage: In welcher Provinz liegt die Talsperre Valdeobispo? Antwort: Die Talsperre Valdeobispo befindet sich in der Provinz Cáceres, Spanien.Frage: Wer betreibt die Talsperre Valdeobispo? Antwort: Die Talsperre Valdeobispo wird von der Confederación Hidrográfica del Tajo betrieben.",
    #     2: "Frage: Wie hoch ist die Höhe der Mauerkrone über dem Meeresspiegel? Antwort: 312 m. Frage: Wie hoch ist das Bemessungshochwasser? Antwort: 1354 m³/s.",
    #     3: "Frage: Wie hoch ist die Höhe der Mauerkrone über dem Meeresspiegel? Antwort: 312 m. Frage: Wie hoch ist das Bemessungshochwasser? Antwort: 1354 m³/s. Antwort von ChatGPT für Bereich 3: Frage: Wie groß ist die Fläche des Stausees? Antwort: Der Stausee erstreckt sich über eine Fläche von rund 3,57 km². Frage: Wie viel Wasser kann genutzt werden? Antwort: 53 Mio. m³ Wasser können genutzt werden. Frage: Wie lang ist der Stausee? Antwort: Der Stausee erstreckt sich über eine Länge von 17 km.",
    #     4: "] Frage: Wie hoch ist die installierte Leistung des Kraftwerks? Antwort: 405 MW. Frage: Wie hoch ist die Fallhöhe? Antwort: 47 m. Frage: Wie hoch liegt der maximale Durchfluss? Antwort: 50 m³/s für jede der beiden Turbinen. Frage: Wie hoch ist die Nenndrehzahl der Turbinen? Antwort: 230 Umdrehungen pro Minute.",
    #     5: "Teil des Flussbeckens Tajo Frage: Wo befindet sich die Talsperre Valdeobispo? Antwort: Die Talsperre Valdeobispo befindet sich in Spanien, Provinz Cáceres. Frage: Welches Gewässer schützt die Talsperre Valdeobispo? Antwort: Die Talsperre Valdeobispo schützt den Alagón. Frage: Wie hoch ist der Oberwasserpegel der Talsperre Valdeobispo? Antwort: Der Oberwasserpegel der Talsperre Valdeobispo beträgt 308 Meter. Frage: Wer ist Eigentümer der Talsperre Valdeobispo? Antwort: Der Eigentümer der Talsperre Valdeobispo ist der Staat. Frage: Wer betreibt die Talsperre Valdeobispo? Antwort: Die Talsperre Valdeobispo wird von Iberdrola betrieben. Frage: Seit wann wird die Talsperre Valdeobispo betrieben? Antwort: Die Talsperre Valdeobispo wird seit 1968 betrieben.",
    # }

    section_responses = {}

    for idx, section in enumerate(sections):
        prompt = 'Generiere Fragen und Antworten aus dem gegebenen Text, nutze alle Informationen. Verwende ausnahmslos das Format: Frage: Antwort:. Text: ' + section
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=500
        )
        chatgpt_response = response.choices[0].text.strip()

        custom_print(
            f"\n---GPT-Antwort für Abschnitt {idx+1}:\n{chatgpt_response}\n")

        lines = chatgpt_response.split("\n")
        lines_joined = " ".join(lines)

        pairs = [pair for pair in lines_joined.split(
            "Frage:") if " Antwort:" in pair]

        section_responses[idx + 1] = []
        for pair in pairs:
            splitted = pair.split(" Antwort:")
            if len(splitted) == 2:
                question = splitted[0].strip()
                answer = splitted[1].strip()
                section_responses[idx + 1].extend([question, answer])

    # AUSGABE der GPT-Fragen/Antworten
    for section_num, responses in section_responses.items():
        custom_print(f"\n----- Abschnitt {section_num} -----")
        for i in range(0, len(responses), 2):
            print(f"{(i//2)+1}. Frage: {responses[i]}")
            print(f"{(i//2)+1}. Antwort: {responses[i+1]}")

    if not get_user_confirmation("\nBestätigen Sie die Richtigkeit der generierten Fragen & Antworten?"):
        custom_print(
            "\nGenerierung vom Benutzer abgebrochen. Rückkehr zum Menü.", LogLevel.INFO)
        return

    ############################################
    # Schritt 6: Formatieren der generierten Fragen und Antworten in JSONL
    format_and_save_questions(section_responses, raw_data_filename)

    custom_print("\nRückkehr zum Hauptmenü.", LogLevel.INFO)


def format_and_save_questions(section_responses, raw_data_filename):
    # Das Endzeichen für den prompt:
    PROMPT_END = "\n\n###\n\n"
    # Start und Ende des completion-Teils:
    COMPLETION_START = " "
    COMPLETION_END = " END"

    # Sammeln der Ausgabe für den Benutzer:
    output_list = []

    for section_num, responses in section_responses.items():
        for i in range(0, len(responses), 2):
            prompt = responses[i] + PROMPT_END
            completion = COMPLETION_START + responses[i+1] + COMPLETION_END
            output_list.append({"prompt": prompt, "completion": completion})

    # Ausgabe im Terminal anzeigen:
    custom_print("\nGenerierte JSONL-Daten:\n")
    for item in output_list:
        print(json.dumps(item, ensure_ascii=False))
        print()

    # Benutzer nach Speicherung der Daten in einer Datei fragen:
    if not get_user_confirmation("\nBestätigen Sie die Richtigkeit der generierten Daten?"):
        custom_print(
            "\nSpeicherung vom Benutzer abgebrochen. Rückkehr zum Menü.", LogLevel.INFO)
        return

    # Dateinamen bestimmen:
    while True:
        if get_user_choice("\nMöchten Sie den Namen der Rohdatendatei verwenden [1] oder einen Dateinamen wählen [2]?: ", 1, 2) == 2:
            filename = custom_input(
                "\nBitte geben Sie den gewünschten Dateinamen ohne Erweiterung an: ") + ".jsonl"
        else:
            filename = raw_data_filename + ".jsonl"

        file_path = os.path.join(PREPARED_DATA_DIR, filename)

        if os.path.exists(file_path):
            if get_user_confirmation(f"Die Datei '{filename}' existiert bereits. Möchten Sie sie überschreiben?"):
                break
            else:
                custom_print(
                    "Bitte wählen Sie einen anderen Dateinamen oder entscheiden Sie sich dafür, die vorhandene Datei zu überschreiben.", LogLevel.INFO)
                continue
        else:
            break

    # Die generierten Daten in eine Datei speichern:
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in output_list:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    custom_print(f"\nDaten wurden in {file_path} gespeichert.", LogLevel.INFO)

    if get_user_confirmation("\nMöchten Sie eine OpenAI-Validierung durchführen?"):
        command = f'start cmd /k openai tools fine_tunes.prepare_data -f {file_path}'
        open_terminal_with_command(command)


def read_and_prepare_data():
    print_header(
        "Formatierung von bestehenden Fragen und Antworten in das Zielformat (.jsonl)")
    custom_print("Die Daten in der .txt-Datei müssen folgendes Format haben, damit sie von der Funktion 'read_and_prepare_data' korrekt verarbeitet werden können:")
    custom_print(
        "1. Jede Frage muss mit dem Präfix 'Frage:' beginnen.", LogLevel.INFO)
    custom_print(
        "2. Jede Antwort muss mit dem Präfix 'Antwort:' beginnen.", LogLevel.INFO)
    custom_print(
        "3. Jede Frage muss einer Antwort folgen, und umgekehrt.", LogLevel.INFO)
    custom_print("4. Die Schlüsselwörter 'Frage:' und 'Antwort:' sollten nur für ihre jeweiligen Rollen verwendet werden und dürfen nicht im Text der Fragen oder Antworten vorkommen.", LogLevel.INFO)
    custom_print(
        "5. Fragen und Antworten können auf der gleichen Zeile oder auf verschiedenen Zeilen stehen.", LogLevel.INFO)
    custom_print(
        "6. Zeilenumbrüche innerhalb von Fragen oder Antworten sind nicht erforderlich, da sie ignoriert werden.", LogLevel.INFO)

    if get_user_choice("\nMöchten Sie eine Datei aus dem definierten Verzeichnis '" + RAW_DATA_DIR + "' wählen [1] oder den absoluten Pfad einer .txt-Datei angeben [2]?", 1, 2) == 1:
        # Dateien in RAW_DATA_DIR auflisten
        files = [f for f in os.listdir(RAW_DATA_DIR) if os.path.isfile(
            os.path.join(RAW_DATA_DIR, f))]
        for idx, filename in enumerate(files):
            print(f"{idx+1}. {filename}")
        file_idx = get_user_choice(
            "Wählen Sie die Nummer der Datei aus: ", 1, len(files)) - 1
        file_path = os.path.join(RAW_DATA_DIR, files[file_idx])
    else:
        file_path = custom_input(
            "Bitte geben Sie den vollständigen Pfad zur TXT-Datei ein: ")
        # Datei einlesen
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Entfernen Sie alle Zeilenumbrüche, da sie in diesem Fall nicht nützlich sind
    lines_joined = content.replace("\n", " ")

    section_responses = {}
    current_section = 1 
    section_responses[current_section] = []

    pairs = [pair for pair in lines_joined.split(
        "Frage:") if " Antwort:" in pair]

    for pair in pairs:
        splitted = pair.split(" Antwort:")
        if len(splitted) == 2:
            question = splitted[0].strip()
            answer = splitted[1].strip()
            section_responses[current_section].extend([question, answer])

    raw_data_filename = os.path.basename(file_path)
    format_and_save_questions(section_responses, raw_data_filename)
