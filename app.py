import os
import ffmpeg
from flask import (
    Flask, request, render_template, send_from_directory, 
    jsonify, url_for
)
from werkzeug.utils import secure_filename

# --- Konfiguracja ---
UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'

# Definicja dozwolonych formatów (wejściowych i docelowych)
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'bmp',    # Obrazy
    'flv', 'mov', 'mp4', 'avi',     # Wideo
    'wav', 'mp3', '3gp', 'midi',    # Audio
}
TARGET_EXTENSIONS = {'jpg', 'png', 'bmp', 'mp4', 'avi', 'mov', 'flv', 'mp3', 'wav', '3gp', 'midi'} # Wszystkie opcje z selecta

# Limit 10MB na plik
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 Megabajtów

# Słowniki do kategoryzacji formatów
IMAGE_FORMATS = {'jpg', 'jpeg', 'png', 'bmp'}
VIDEO_FORMATS = {'flv', 'mov', 'mp4', 'avi'}
AUDIO_FORMATS = {'wav', 'mp3', '3gp', 'midi'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 # Ustawiamy globalny limit rozmiaru requestu

# --- Funkcje pomocnicze ---

def allowed_file(filename):
    """Sprawdza, czy plik ma dozwolone rozszerzenie wejściowe."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_target_format_allowed(format_ext):
    """Sprawdza, czy format docelowy jest na liście dozwolonych."""
    return format_ext.lower() in TARGET_EXTENSIONS

def get_file_type(extension):
    """Zwraca typ pliku (image, video, audio) na podstawie rozszerzenia."""
    ext = extension.lower()
    if ext in IMAGE_FORMATS:
        return 'image'
    if ext in VIDEO_FORMATS:
        return 'video'
    if ext in AUDIO_FORMATS:
        return 'audio'
    return None

def apply_quality_settings(stream, file_type, output_path):
    """
    Stosuje ustawienia jakości dla kompresji zgodnie z założeniem "utraty do 90%".
    """
    ext = output_path.rsplit('.', 1)[-1].lower()
    
    # Dla większości konwersji
    if file_type == 'video':
        # CRF=30 dla zauważalnej kompresji, profil i presety dla optymalizacji MP4
        return ffmpeg.output(stream, output_path, crf=30, vcodec='libx264', preset='veryfast', acodec='aac', strict='experimental')
    
    elif file_type == 'audio':
        # Audio bitrate 96k - dobra kompresja
        return ffmpeg.output(stream, output_path, audio_bitrate='96k')
    
    elif file_type == 'image':
        if ext in ('jpg', 'jpeg'):
            # Jakość 1-31. 8-10 to zauważalna kompresja
            return ffmpeg.output(stream, output_path, qscale=8) 
        # PNG jest bezstratny, więc konwersja do PNG nie będzie mocno kompresować
        # Inne formaty, domyślna konwersja
    
    # Domyślnie
    return ffmpeg.output(stream, output_path)

# --- Trasy (Routes) ---

@app.route('/')
def index():
    """Wyświetla główną stronę z formularzem."""
    # Ze względu na brak pliku templates/index.html w tej interakcji
    # Używamy render_template, ale MUSISZ umieścić HTML w templates/index.html
    # Jeśli chcesz, mogę Ci go wysłać w kolejnej odpowiedzi.
    # W tej chwili zakładam, że używasz render_template.
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """Obsługuje przesyłanie i konwersję plików."""
    results = []
    errors = []

    # 1. Walidacja formatu docelowego
    target_format = request.form.get('format')
    if not target_format or not is_target_format_allowed(target_format):
        errors.append('Nie wybrano lub wybrano nieobsługiwany format docelowy.')
        return jsonify({'errors': errors}), 400
    
    target_type = get_file_type(target_format)

    # 2. Walidacja plików
    if 'files' not in request.files or not request.files.getlist('files'):
        errors.append('Nie wybrano żadnych plików.')
        return jsonify({'errors': errors}), 400

    files = request.files.getlist('files')

    # 3. Przetwarzanie każdego pliku
    for file in files:
        if file.filename == '':
            continue
        
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not allowed_file(filename):
            errors.append(f'Plik "{filename}" ma niedozwolone rozszerzenie.')
            continue
        
        input_ext = filename.rsplit('.', 1)[1].lower()
        input_type = get_file_type(input_ext)

        # Sprawdzenie zgodności typów
        if input_type != target_type:
            errors.append(f'Nie można konwertować "{filename}" ({input_type}) na format typu {target_type} ({target_format}).')
            continue

        # Zapisz plik tymczasowo
        try:
            file.save(input_path)
            # Sprawdzenie rozmiaru pliku *po* zapisaniu
            file_size = os.path.getsize(input_path)
            if file_size > MAX_FILE_SIZE:
                errors.append(f'Plik "{filename}" jest za duży (limit 10MB).')
                os.remove(input_path)
                continue
        except Exception as e:
            errors.append(f'Błąd podczas zapisywania lub sprawdzania rozmiaru "{filename}": {e}')
            if os.path.exists(input_path):
                 os.remove(input_path)
            continue

        # Przygotowanie konwersji
        base_filename = filename.rsplit('.', 1)[0]
        output_filename = f"{base_filename}_converted.{target_format}"
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

        try:
            # Konwersja za pomocą ffmpeg
            stream = ffmpeg.input(input_path)
            stream = apply_quality_settings(stream, target_type, output_path)
            ffmpeg.run(stream, overwrite_output=True, quiet=False)

            # Jeśli sukces
            results.append({
                'original': filename,
                'converted': output_filename,
                'download_url': url_for('download', filename=output_filename)
            })

        except ffmpeg.Error as e:
            # Wypisz komunikat z ffmpeg, jeśli błąd jest z nim związany
            error_message = e.stderr.decode("utf-8", errors='ignore') if e.stderr else "Nieznany błąd ffmpeg."
            errors.append(f'Błąd konwersji "{filename}": {error_message[:100]}...') # Ogranicz do 100 znaków
        except Exception as e:
            errors.append(f'Nieoczekiwany błąd podczas przetwarzania "{filename}": {e}')
        
        finally:
            # Usuń oryginalny plik po konwersji (lub błędzie)
            if os.path.exists(input_path):
                os.remove(input_path)
                
    return jsonify({'results': results, 'errors': errors})


@app.route('/download/<filename>')
def download(filename):
    """Udostępnia przekonwertowany plik do pobrania."""
    return send_from_directory(
        app.config['CONVERTED_FOLDER'], 
        filename, 
        as_attachment=True
    )

# --- Uruchomienie ---
if __name__ == '__main__':
    # Utwórz foldery, jeśli nie istnieją
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(CONVERTED_FOLDER, exist_ok=True)
    app.run(debug=True)