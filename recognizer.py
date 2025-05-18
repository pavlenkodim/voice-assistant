import os
import tempfile
import time
import speech_recognition as sr
import whisper
import numpy as np
import torch

class SpeechRecognizer:
    """Класс для распознавания речи с использованием различных моделей."""
    
    def __init__(self, use_whisper=True, whisper_model="base", language="ru"):
        """
        Инициализация распознавателя речи.
        
        Args:
            use_whisper (bool): Использовать Whisper вместо Google Speech Recognition
            whisper_model (str): Размер модели Whisper ("tiny", "base", "small", "medium", "large")
            language (str): Язык распознавания (для Whisper и Google Speech)
        """
        self.recognizer = sr.Recognizer()
        self.use_whisper = use_whisper
        self.language = language
        
        # Инициализация модели Whisper, если она выбрана
        if use_whisper:
            self.whisper_model = whisper.load_model(whisper_model)
            print(f"Модель Whisper '{whisper_model}' загружена")
    
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
            return self._recognize_with_whisper(audio)
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
    
    def _recognize_with_whisper(self, audio):
        """Распознавание с помощью локальной модели Whisper."""
        try:
            # Создаем имя для временного файла
            temp_dir = tempfile.gettempdir()
            temp_filename = os.path.join(temp_dir, f"whisper_audio_{int(time.time())}.wav")
            
            # Сохраняем аудио во временный файл
            with open(temp_filename, 'wb') as temp_audio:
                temp_audio.write(audio.get_wav_data())
            
            # Даем системе время на закрытие файла
            time.sleep(0.5)
            
            # Проверяем, существует ли файл
            if not os.path.exists(temp_filename):
                raise FileNotFoundError(f"Временный файл не был создан: {temp_filename}")
            
            # Распознаем с помощью Whisper
            result = self.whisper_model.transcribe(
                temp_filename,
                language=self.language,
                fp16=torch.cuda.is_available()
            )
            
            # Удаляем временный файл
            os.remove(temp_filename)
            
            text = result["text"].strip()
            print(f"Распознано (Whisper): {text}")
            return text.lower()
        except Exception as e:
            print(f"Ошибка при распознавании Whisper: {e}")
            return None


# Пример использования
if __name__ == "__main__":
    # Тестируем распознаватель
    recognizer = SpeechRecognizer(use_whisper=True, whisper_model="base")
    result = recognizer.listen()
    print(f"Результат: {result}") 