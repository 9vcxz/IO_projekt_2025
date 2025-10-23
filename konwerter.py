import os
from PIL import Image
from moviepy.editor import VideoFileClip, AudioFileClip

# --- Konwersja Obrazów (Wymaga Pillow: pip install Pillow) ---

def convert_image(input_filepath, target_format, jpeg_quality=90):
    """
    Konwertuje plik obrazu do formatu PNG, JPEG lub BMP.

    :param input_filepath: Ścieżka do pliku wejściowego.
    :param target_format: Docelowy format ('PNG', 'JPEG', 'BMP').
    :param jpeg_quality: Jakość JPEG (0-100), domyślnie 90% (stratna).
    :return: Ścieżka do przekonwertowanego pliku lub None w przypadku błędu.
    """
    target_format = target_format.upper()
    valid_formats = {'JPEG', 'PNG', 'BMP'}

    if target_format not in valid_formats:
        print(f"Błąd: Nieobsługiwany format obrazu: {target_format}. Wybierz spośród {', '.join(valid_formats)}")
        return None

    # Tworzenie nazwy pliku wyjściowego
    base, ext = os.path.splitext(input_filepath)
    output_filepath = f"{base}_converted.{target_format.lower()}"

    try:
        with Image.open(input_filepath) as img:
            if target_format == 'JPEG':
                img.save(output_filepath, format='JPEG', quality=jpeg_quality)
            elif target_format == 'BMP':
                 # Upewnienie się, że obraz ma odpowiedni tryb przed konwersją do BMP
                if img.mode == 'P':
                    img = img.convert('RGB')
                img.save(output_filepath, format='BMP')
            else: # PNG
                img.save(output_filepath, format=target_format)
            
        print(f"Obraz '{input_filepath}' skonwertowany do '{output_filepath}'")
        return output_filepath
    except FileNotFoundError:
        print(f"Błąd: Plik nie znaleziony: {input_filepath}")
        return None
    except Exception as e:
        print(f"Błąd konwersji obrazu: {e}")
        return None

# -----------------------------------------------------------------
# --- Konwersja Wideo i Audio (Wymaga FFmpeg i moviepy: pip install moviepy) ---
# -----------------------------------------------------------------

def convert_media(input_filepath, target_format, media_type):
    """
    Konwertuje plik wideo lub audio do określonego formatu.
    (Wymaga FFmpeg i moviepy)

    :param input_filepath: Ścieżka do pliku wejściowego.
    :param target_format: Docelowy format ('FLV', 'AVI', 'MOV', 'MP4', 'MP3', 'WAV', '3GP', 'MIDI').
    :param media_type: Typ multimediów ('video' lub 'audio').
    :return: Ścieżka do przekonwertowanego pliku lub None w przypadku błędu.
    """
    target_format = target_format.lower().replace('3gg', '3gp') # Korekta 3GG na 3GP
    
    # Mapowanie formatów na rozszerzenia (używane przez moviepy/FFmpeg)
    video_formats = {'flv', 'avi', 'mov', 'mp4'}
    audio_formats = {'mp3', 'wav', '3gp', 'midi'} # MIDI to specyficzny format, FFmpeg może mieć problemy lub wymagać dodatkowych kroków

    if media_type == 'video' and target_format not in video_formats:
        print(f"Błąd: Nieobsługiwany format wideo: {target_format}. Wybierz spośród {', '.join(video_formats)}")
        return None
    elif media_type == 'audio' and target_format not in audio_formats:
        print(f"Błąd: Nieobsługiwany format audio: {target_format}. Wybierz spośród {', '.in(audio_formats)}")
        return None

    # Tworzenie nazwy pliku wyjściowego
    base, ext = os.path.splitext(input_filepath)
    output_filepath = f"{base}_converted.{target_format}"

    try:
        if media_type == 'video':
            # Użycie VideoFileClip dla konwersji wideo
            with VideoFileClip(input_filepath) as clip:
                clip.write_videofile(
                    output_filepath, 
                    codec='libx264', # Typowy kodek dla większości kontenerów, może wymagać dostosowania
                    audio_codec='aac' if target_format == 'mp4' else 'mp3', # Domyślny kodek audio
                    verbose=False, logger=None
                )
        elif media_type == 'audio':
            # Uwaga: Konwersja do MIDI jest bardzo specyficznym zadaniem
            # (extrakcja nut, a nie zmiana kontenera) i wymaga specjalistycznych
            # bibliotek (np. Musescore, Music21). FFmpeg/moviepy tego standardowo nie robi.
            if target_format == 'midi':
                print("Ostrzeżenie: Konwersja do MIDI wymaga zaawansowanych narzędzi do ekstrakcji nut i nie jest wspierana przez FFmpeg/moviepy. Zostanie pominięta.")
                return None
                
            # Użycie AudioFileClip dla konwersji audio
            with AudioFileClip(input_filepath) as clip:
                clip.write_audiofile(
                    output_filepath, 
                    codec='libmp3lame' if target_format == 'mp3' else None,
                    verbose=False, logger=None
                )
                
        print(f"Plik {media_type} '{input_filepath}' skonwertowany do '{output_filepath}'")
        return output_filepath
    except FileNotFoundError:
        print(f"Błąd: Plik wejściowy nie znaleziony: {input_filepath}")
        return None
    except Exception as e:
        print(f"Błąd konwersji {media_type}: Upewnij się, że masz zainstalowany FFmpeg i moviepy: {e}")
        return None

# --- Przykłady Użycia ---

# 1. Obraz
# Utwórz fikcyjny plik 'test.jpg' lub użyj ścieżki do prawdziwego pliku.
# print("\n--- Test Obrazu ---")
# image_path = "path/do/twojego/obrazu.png"
# # convert_image(image_path, "JPEG", jpeg_quality=85) # Konwersja do JPEG (85% jakości)
# # convert_image(image_path, "PNG") # Konwersja do PNG
# # convert_image(image_path, "BMP") # Konwersja do BMP

# 2. Wideo
# Utwórz fikcyjny plik 'test.mp4' lub użyj ścieżki do prawdziwego pliku.
# print("\n--- Test Wideo ---")
# video_path = "path/do/twojego/wideo.mov"
# # convert_media(video_path, "MP4", "video")
# # convert_media(video_path, "AVI", "video")

# 3. Dźwięk
# Utwórz fikcyjny plik 'test.wav' lub użyj ścieżki do prawdziwego pliku.
# print("\n--- Test Audio ---")
# audio_path = "path/do/twojego/audio.wav"
# # convert_media(audio_path, "MP3", "audio")
# # convert_media(audio_path, "WAV", "audio")
# # convert_media(audio_path, "3GP", "audio")