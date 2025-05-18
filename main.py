#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import signal
import sys
import string
import pyautogui
import keyboard
from dotenv import load_dotenv
from recognizer import SpeechRecognizer
from executor import CommandExecutor

# Загрузка переменных окружения
load_dotenv()

# Словарь для преобразования знаков препинания, произнесенных на русском
PUNCTUATION_MAP = {
    "точка": ".",
    "запятая": ",",
    "вопрос": "?",
    "восклицательный знак": "!",
    "двоеточие": ":",
    "точка с запятой": ";",
    "тире": "-",
    "дефис": "-",
    "скобка открывается": "(",
    "скобка закрывается": ")",
    "кавычки": "\"",
    "новая строка": "\n",
    "абзац": "\n\n"
}

class VoiceAssistant:
    """Основной класс голосового ассистента."""
    
    def __init__(self, use_whisper=False, whisper_model="base"):
        """
        Инициализация голосового ассистента.
        
        Args:
            use_whisper (bool): Использовать Whisper вместо Google Speech Recognition
            whisper_model (str): Размер модели Whisper
        """
        self.recognizer = SpeechRecognizer(use_whisper=use_whisper, whisper_model=whisper_model)
        self.executor = CommandExecutor()
        self.running = False
        self.learning_mode = False
        self.dictation_mode = False
        
        # Настройка обработчика сигналов для корректного завершения
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def start(self):
        """Запуск основного цикла голосового ассистента."""
        self.running = True
        print("Голосовой ассистент запущен. Нажмите Ctrl+C для выхода.")
        
        self.executor.speak("Голосовой ассистент готов к работе")
        
        while self.running:
            try:
                # Распознавание голосовой команды
                command = self.recognizer.listen(timeout=5, phrase_time_limit=10)
                
                if command:
                    if self.learning_mode:
                        self._handle_learning_mode(command)
                    elif self.dictation_mode:
                        self._handle_dictation_mode(command)
                    elif "режим обучения" in command:
                        self._enter_learning_mode()
                    elif "режим диктовки" in command:
                        self._enter_dictation_mode()
                    elif command.lower() in ["стоп", "выход", "завершить"]:
                        self._shutdown()
                    else:
                        # Обработка обычной команды
                        result = self.executor.process_command(command)
                        
                        if not result:
                            print("Команда не распознана или не выполнена")
                
                # Небольшая пауза для снижения нагрузки на CPU
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Ошибка в основном цикле: {e}")
    
    def _enter_learning_mode(self):
        """Вход в режим обучения для добавления новых команд."""
        self.learning_mode = True
        self.executor.speak("Режим обучения активирован. Скажите команду, которую нужно запомнить.")
        print("=== РЕЖИМ ОБУЧЕНИЯ ===")
        print("1. Произнесите текст команды")
        print("2. Затем произнесите действие в формате: тип параметры")
        print("Например: открой chrome")
    
    def _handle_learning_mode(self, command):
        """
        Обработка команд в режиме обучения.
        
        Args:
            command (str): Распознанная голосовая команда
        """
        if not hasattr(self, 'learning_step'):
            self.learning_step = 1
            self.new_trigger = None
            self.new_action = None
        
        if self.learning_step == 1:
            # Первый шаг: запоминаем триггер команды
            self.new_trigger = command
            print(f"Триггер команды: {command}")
            self.executor.speak(f"Записал триггер команды. Теперь скажите действие.")
            self.learning_step = 2
        
        elif self.learning_step == 2:
            # Второй шаг: запоминаем действие
            self.new_action = command
            print(f"Действие команды: {command}")
            
            # Добавляем новую команду
            if self.executor.add_new_command(self.new_trigger, self.new_action):
                self.executor.speak("Команда успешно добавлена")
            else:
                self.executor.speak("Ошибка при добавлении команды")
            
            # Выход из режима обучения
            self.learning_mode = False
            delattr(self, 'learning_step')
            delattr(self, 'new_trigger')
            delattr(self, 'new_action')
            
            print("=== РЕЖИМ ОБУЧЕНИЯ ЗАВЕРШЕН ===")
    
    def _enter_dictation_mode(self):
        """Вход в режим диктовки для непрерывного ввода текста."""
        self.dictation_mode = True
        self.executor.speak("Режим диктовки активирован. Говорите текст для ввода. Скажите 'стоп диктовку' для выхода.")
        print("=== РЕЖИМ ДИКТОВКИ ===")
        print("Говорите текст для ввода")
        print("Скажите 'стоп диктовку' для выхода из режима")
    
    def _handle_dictation_mode(self, command):
        """
        Обработка команд в режиме диктовки.
        
        Args:
            command (str): Распознанная голосовая команда
        """
        if "стоп диктовку" in command.lower():
            # Выход из режима диктовки
            self.dictation_mode = False
            self.executor.speak("Режим диктовки выключен")
            print("=== РЕЖИМ ДИКТОВКИ ЗАВЕРШЕН ===")
            return
        
        # Обработка команд пунктуации
        for spoken_mark, symbol in PUNCTUATION_MAP.items():
            if spoken_mark in command.lower():
                # Заменяем произнесенную пунктуацию на символы
                command = command.lower().replace(spoken_mark, symbol)
        
        # Очищаем текст от лишних пробелов
        cleaned_text = command.strip()
        if cleaned_text:
            # Вводим распознанный текст
            print(f"Распознано для ввода: '{cleaned_text}'")
            
            # Определяем, содержит ли текст русские символы
            has_russian = any('а' <= c.lower() <= 'я' for c in cleaned_text)
            
            if has_russian:
                self.executor._type_russian_text(cleaned_text)
            else:
                # Для английского текста и символов используем простой способ
                keyboard.write(cleaned_text)
                
            # Добавляем пробел только если текст не заканчивается на знак пунктуации
            if cleaned_text[-1] not in string.punctuation and not cleaned_text.endswith("\n"):
                keyboard.press_and_release('space')
        else:
            print("Распознана пустая строка, ввод пропущен")
    
    def _signal_handler(self, sig, frame):
        """Обработчик сигнала для корректного завершения программы."""
        print("\nЗавершение работы голосового ассистента...")
        self.running = False
        sys.exit(0)

    def _shutdown(self):
        """Корректное завершение работы ассистента."""
        print("\nЗавершение работы голосового ассистента...")
        self.executor.speak("Завершаю работу. До свидания!")
        time.sleep(1)  # Даем время для произнесения фразы
        self.running = False
        sys.exit(0)


def main():
    """Точка входа в программу."""
    # Проверка наличия API-ключа OpenAI
    if not os.getenv("OPENAI_API_KEY"):
        print("ВНИМАНИЕ: API-ключ OpenAI не найден. Функционал GPT будет недоступен.")
        print("Создайте файл .env и добавьте в него строку: OPENAI_API_KEY=your_api_key_here")
    
    # Создание и запуск голосового ассистента
    print("Инициализация голосового ассистента...")
    # Используем Google Speech Recognition вместо Whisper из-за проблем с временными файлами
    assistant = VoiceAssistant(use_whisper=False)
    assistant.start()


if __name__ == "__main__":
    main() 