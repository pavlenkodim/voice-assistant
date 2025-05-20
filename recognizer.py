import os
import tempfile
import time
import speech_recognition as sr
from faster_whisper import WhisperModel
import numpy as np
import torch
import warnings

# Игнорируем предупреждения, которые могут возникать в новых версиях Python
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

class SpeechRecognizer:
    """Класс для распознавания речи с использованием различных моделей."""
    
    def __init__(self, use_whisper=True, whisper_model="base", language="ru"):
        """
        Инициализация распознавателя речи.
        
        Args:
            use_whisper (bool): Использовать faster-whisper вместо Google Speech Recognition
            whisper_model (str): Размер модели faster-whisper ("tiny", "base", "small", "medium", "large")
            language (str): Язык распознавания (для faster-whisper и Google Speech)
        """
        self.recognizer = sr.Recognizer()
        self.use_whisper = use_whisper
        self.language = language
        
        # Инициализация модели faster-whisper, если она выбрана
        if use_whisper:
            try:
                # Определяем наличие CUDA для ускорения
                compute_type = "float16" if torch.cuda.is_available() else "int8"
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                # Загружаем модель faster-whisper
                self.whisper_model = WhisperModel(
                    whisper_model, 
                    device=device, 
                    compute_type=compute_type
                )
                print(f"Модель faster-whisper '{whisper_model}' загружена на устройстве {device} с типом {compute_type}")
            except Exception as e:
                print(f"Ошибка загрузки модели faster-whisper: {e}")
                print("Переключение на Google Speech Recognition")
                self.use_whisper = False
    
    def listen(self, timeout=5, phrase_time_limit=None):
        """
        Прослушивание микрофона и запись аудио.
        
        Args:
            timeout (int): Время ожидания начала фразы в секундах
            phrase_time_limit (int): Максимальная длительность записи в секундах
            
        Returns:
            str: Распознанный текст или None в случае ошибки
        """
        try:
            with sr.Microphone() as source:
                print("Слушаю...")
                # Настройка подавления шума для лучшего распознавания
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                
                return self._recognize_audio(audio)
        except sr.WaitTimeoutError:
            print("Время ожидания истекло. Не услышал команду.")
            return None
        except Exception as e:
            print(f"Ошибка при прослушивании: {e}")
            return None
    
    def _recognize_audio(self, audio):
        """
        Распознавание записанного аудио с использованием выбранной модели.
        
        Args:
            audio: Аудиоданные от SpeechRecognition
            
        Returns:
            str: Распознанный текст или None в случае ошибки
        """
        if self.use_whisper:
            return self._recognize_with_faster_whisper(audio)
        else:
            return self._recognize_with_google(audio)
    
    def _recognize_with_google(self, audio):
        """Распознавание с помощью Google Speech Recognition."""
        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
            print(f"Распознано: {text}")
            return text.lower()
        except sr.UnknownValueError:
            print("Не удалось распознать речь")
            return None
        except sr.RequestError as e:
            print(f"Ошибка сервиса Google Speech Recognition: {e}")
            return None
    
    def _recognize_with_faster_whisper(self, audio):
        """Распознавание с помощью локальной модели faster-whisper."""
        try:
            # Создаем уникальное имя для временного файла
            temp_dir = tempfile.gettempdir()
            temp_filename = os.path.join(temp_dir, f"whisper_audio_{int(time.time())}_{os.getpid()}.wav")
            
            # Сохраняем аудио во временный файл
            with open(temp_filename, 'wb') as temp_audio:
                temp_audio.write(audio.get_wav_data())
            
            # Проверяем, существует ли файл
            if not os.path.exists(temp_filename):
                raise FileNotFoundError(f"Временный файл не был создан: {temp_filename}")
            
            # Распознаем с помощью faster-whisper
            # Новый API для faster-whisper
            segments, info = self.whisper_model.transcribe(
                temp_filename,
                language=self.language,
                beam_size=5,
                word_timestamps=False
            )
            
            # Собираем текст из всех сегментов
            text = " ".join([segment.text for segment in segments])
            
            # Удаляем временный файл
            try:
                os.remove(temp_filename)
            except Exception as e:
                print(f"Предупреждение: Не удалось удалить временный файл: {e}")
            
            print(f"Распознано (faster-whisper): {text}")
            return text.lower().strip()
        except Exception as e:
            print(f"Ошибка при распознавании faster-whisper: {e}")
            # Пробуем запасной вариант с Google
            print("Попытка распознать с помощью Google Speech...")
            return self._recognize_with_google(audio)


# Пример использования
if __name__ == "__main__":
    # Тестируем распознаватель
    recognizer = SpeechRecognizer(use_whisper=True, whisper_model="base")
    result = recognizer.listen()
    print(f"Результат: {result}") 