import os
import ffmpeg  # Importujemy ffmpeg-python
from flask import (
    Flask, request, render_template, send_from_directory, 
    jsonify, url_for
)
from werkzeug.utils import secure_filename

# --- Konfiguracja ---
UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'
# Definiujemy dozwolone formaty wejściowe
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'bmp',  # Obrazy
    'flv', 'mov', 'mp4', 'avi',   # Wideo
    'wav', 'mp3', '3gp', 'midi'   # Audio
}
# Limit 10MB na plik
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 Megabajtów

# Słowniki do kategoryzacji formatów
IMAGE_FORMATS = {'jpg', 'jpeg', 'png', 'bmp'}
VIDEO_FORMATS = {'flv', 'mov', 'mp4', 'avi'}
AUDIO_FORMATS = {'wav', 'mp3', '3gp', 'midi'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
# Ustawiamy globalny limit rozmiaru requestu (np. 50MB na batch)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 

# --- Funkcje pomocnicze ---

def allowed_file(filename):
    """Sprawdza, czy plik ma dozwolone rozszerzenie."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    Stosuje ustawienia jakości zgodnie z założeniem "utraty do 90%".
    Używamy tutaj ustawień, które powodują zauważalną kompresję.
    """
    if file_type == 'video':
        # CRF (Constant Rate Factor) - wyższa wartość = gorsza jakość, mniejszy plik.
        # 23 to standard, 30 to już zauważalna kompresja.
        return ffmpeg.output(stream, output_path, crf=30)
    elif file_type == 'audio':
        # Ustawiamy bitrate audio na 96k - dobra kompresja dla prototypu.
        return ffmpeg.output(stream, output_path, audio_bitrate='96k')
    elif file_type == 'image':
        # Ustawiamy skalę jakości (qscale:v) dla obrazów. Niższa = lepsza.
        # Skala 1-31. Wartość 5-10 da zauważalną kompresję.
        return ffmpeg.output(stream, output_path, qscale=5)
    else:
        # Domyślnie, jeśli typ nie jest rozpoznany (choć nie powinno się zdarzyć)
        return ffmpeg.output(stream, output_path)

# --- Trasy (Routes) ---

@app.route('/')
def index():
    """Wyświetla główną stronę z formularzem."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Obsługuje przesyłanie i konwersję plików."""
    if 'files' not in request.files:
        return jsonify({'errors': ['Nie wybrano żadnych plików.']}), 400

    files = request.files.getlist('files')
    target_format = request.form.get('format')

    if not target_format:
        return jsonify({'errors': ['Nie wybrano formatu docelowego.']}), 400

    # Określamy typ docelowy (image, video, audio)
    target_type = get_file_type(target_format)
    if not target_type:
        return jsonify({'errors': [f'Nieobsługiwany format docelowy: {target_format}']}), 400

    results = []
    errors = []

    for file in files:
        if file and file.filename == '':
            continue  # Pomiń puste sloty plików

        if not allowed_file(file.filename):
            errors.append(f'Plik "{file.filename}" ma niedozwolone rozszerzenie.')
            continue

        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Zapisz plik tymczasowo
        try:
            file.save(input_path)
        except Exception as e:
            errors.append(f'Błąd podczas zapisywania "{filename}": {e}')
            continue

        # Sprawdzenie rozmiaru pliku *po* zapisaniu
        try:
            file_size = os.path.getsize(input_path)
            if file_size > MAX_FILE_SIZE:
                errors.append(f'Plik "{filename}" jest za duży (limit 10MB).')
                os.remove(input_path)  # Usuń za duży plik
                continue
        except OSError as e:
            errors.append(f'Nie można sprawdzić rozmiaru pliku "{filename}": {e}')
            continue

        # Sprawdzenie zgodności typów
        input_ext = filename.rsplit('.', 1)[1].lower()
        input_type = get_file_type(input_ext)

        if input_type != target_type:
            errors.append(f'Nie można konwertować "{filename}" ({input_type}) na format typu {target_type} ({target_format}).')
            os.remove(input_path) # Usuń plik
            continue

        # Przygotowanie konwersji
        base_filename = filename.rsplit('.', 1)[0]
        output_filename = f"{base_filename}_converted.{target_format}"
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

        try:
            # Użycie ffmpeg-python
            stream = ffmpeg.input(input_path)
            stream = apply_quality_settings(stream, target_type, output_path)
            
            # Uruchomienie konwersji
            # .run() śledzi postęp, ale przechwycenie go wymaga skomplikowanej obsługi stderr.
            # Dla prototypu, po prostu czekamy na zakończenie.
            # `overwrite_output=True` pozwala nadpisać plik, jeśli już istnieje.
            ffmpeg.run(stream, overwrite_output=True, quiet=True) # quiet=True ukrywa logi ffmpeg

            # Jeśli sukces, dodaj do wyników
            results.append({
                'original': filename,
                'converted': output_filename,
                'download_url': url_for('download', filename=output_filename)
            })

        except ffmpeg.Error as e:
            errors.append(f'Błąd konwersji "{filename}": {e.stderr.decode("utf-8") if e.stderr else "Nieznany błąd ffmpeg"}')
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