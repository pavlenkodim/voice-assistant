import json
import os
import subprocess
import webbrowser
import pyautogui
import keyboard
import time
import openai
import pyperclip
from dotenv import load_dotenv
import pyttsx3

# Загрузка переменных окружения из .env файла
load_dotenv()

class CommandExecutor:
    """Класс для исполнения голосовых команд и взаимодействия с GPT."""
    
    def __init__(self, config_file="config.json"):
        """
        Инициализация исполнителя команд.
        
        Args:
            config_file (str): Путь к файлу конфигурации с командами
        """
        self.commands = self._load_commands(config_file)
        self.config_file = config_file
        
        # Настройка OpenAI API
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Инициализация движка синтеза речи
        self.tts_engine = pyttsx3.init()
        # Настройка голоса (можно выбрать русский, если доступен)
        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            # Проверяем, есть ли русский голос
            if 'russian' in voice.name.lower() or 'русский' in voice.name.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
        
        # Ключевые слова для активации GPT
        self.gpt_triggers = ["спроси у gpt", "помощник", "спроси у жпт"]
    
    def _load_commands(self, config_file):
        """Загрузка команд из JSON-файла."""
        try:
            with open(config_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            return []
    
    def _switch_keyboard_layout(self):
        """Переключить раскладку клавиатуры с английской на русскую или наоборот"""
        if os.name == 'nt':  # Windows
            # Alt+Shift для переключения раскладки в Windows
            keyboard.press('alt')
            keyboard.press('shift')
            keyboard.release('shift')
            keyboard.release('alt')
        else:  # Linux/Mac
            # Super+Space для переключения раскладки в Linux
            keyboard.press('command')  # или 'super' в некоторых конфигурациях
            keyboard.press_and_release('space')
            keyboard.release('command')
        
        time.sleep(0.2)  # Даем время на переключение
    
    def _type_russian_text(self, text):
        """
        Ввод русского текста с переключением раскладки.
        
        Args:
            text (str): Текст для ввода на русском
        """
        # Сначала переключаем на русскую раскладку
        self._switch_keyboard_layout()
        
        try:
            # Пытаемся напечатать текст обычным способом
            keyboard.write(text)
        except Exception as e:
            print(f"Ошибка при вводе текста целиком: {e}")
            # Если не получилось, используем посимвольный ввод
            self._type_text(text)
        
        # Переключаем обратно на английскую раскладку
        self._switch_keyboard_layout()
    
    def _type_text(self, text):
        """
        Ввод текста посимвольно с прямым нажатием клавиш.
        
        Args:
            text (str): Текст для ввода
        """
        # Таблица соответствия русских букв к клавишам QWERTY
        rus_to_eng = {
            'а': 'f', 'б': ',', 'в': 'd', 'г': 'u', 'д': 'l', 'е': 't', 'ё': '`', 'ж': ';',
            'з': 'p', 'и': 'b', 'й': 'q', 'к': 'r', 'л': 'k', 'м': 'v', 'н': 'y', 'о': 'j',
            'п': 'g', 'р': 'h', 'с': 'c', 'т': 'n', 'у': 'e', 'ф': 'a', 'х': '[', 'ц': 'w',
            'ч': 'x', 'ш': 'i', 'щ': 'o', 'ъ': ']', 'ы': 's', 'ь': 'm', 'э': "'", 'ю': '.',
            'я': 'z', ' ': ' '
        }
        
        print(f"Посимвольный ввод текста: {text}")
        
        # Нужно ли переключить раскладку на русскую
        needs_russian = any(char.lower() in rus_to_eng for char in text if char.isalpha())
        
        for char in text:
            try:
                if char.lower() in rus_to_eng and char.isalpha():
                    # Пробуем переключить на русскую раскладку и напечатать
                    key_to_press = rus_to_eng[char.lower()]
                    
                    # Для заглавных букв
                    if char.isupper():
                        keyboard.press('shift')
                        keyboard.press_and_release(key_to_press)
                        keyboard.release('shift')
                    else:
                        keyboard.press_and_release(key_to_press)
                else:
                    # Для символов, которые одинаковы в обеих раскладках (цифры, знаки и т.д.)
                    keyboard.press_and_release(char)
                    
                time.sleep(0.02)  # Небольшая задержка между символами
            except Exception as e:
                print(f"Ошибка при вводе символа '{char}': {e}")
                # Для сложных символов используем альтернативный метод
                try:
                    keyboard.write(char)
                    time.sleep(0.02)
                except:
                    pass
    
    def process_command(self, text):
        """
        Обработка распознанного текста.
        
        Args:
            text (str): Распознанный текст
            
        Returns:
            bool: True, если команда была обработана, иначе False
        """
        if not text:
            return False
        
        # Проверяем, является ли запрос для голосового ввода
        if text.startswith("напечатай"):
            # Удаляем слово "напечатай" и оставляем только текст для ввода
            input_text = text.replace("напечатай", "", 1).strip()
            if input_text:
                print(f"Ввод текста: '{input_text}'")
                
                # Определяем, содержит ли текст русские символы
                has_russian = any('а' <= c.lower() <= 'я' for c in input_text)
                
                if has_russian:
                    self._type_russian_text(input_text)
                else:
                    keyboard.write(input_text)
                    
                return True
            else:
                self.speak("После команды 'напечатай' нужно указать текст")
                return False
        
        # Проверяем, является ли запрос обращением к GPT
        for trigger in self.gpt_triggers:
            if trigger in text:
                # Удаляем триггер из запроса и отправляем остаток в GPT
                query = text.replace(trigger, "").strip()
                self._ask_gpt(query)
                return True
        
        # Проверяем наличие команды в конфигурации
        for command in self.commands:
            if command["trigger"] in text:
                return self._execute_action(command["action"])
        
        # Команда не найдена
        self.speak("Команда не распознана")
        return False
    
    def _execute_action(self, action):
        """
        Выполнение действия на основе команды.
        
        Args:
            action (str): Строка с действием из конфига
            
        Returns:
            bool: True, если действие выполнено успешно
        """
        try:
            parts = action.split()
            action_type = parts[0].lower()
            
            if action_type == "exit":
                # Завершение программы
                print("Завершение работы голосового ассистента...")
                self.speak("Завершаю работу. До свидания!")
                import sys
                sys.exit(0)
            
            elif action_type == "open":
                # Открытие программы
                program = " ".join(parts[1:])
                if os.name == 'nt':  # Windows
                    os.system(f"start {program}")
                else:  # Linux/Mac
                    subprocess.Popen([program], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            elif action_type == "url":
                # Открытие URL в браузере
                url = parts[1]
                webbrowser.open(url)
            
            elif action_type == "type":
                # Ввод текста
                text = " ".join(parts[1:])
                pyautogui.write(text)
            
            elif action_type == "hotkey":
                # Нажатие горячих клавиш
                keys = parts[1:]
                pyautogui.hotkey(*keys)
            
            elif action_type == "press":
                # Нажатие одной клавиши
                key = parts[1]
                pyautogui.press(key)
            
            else:
                print(f"Неизвестный тип действия: {action_type}")
                return False
            
            print(f"Выполнено действие: {action}")
            return True
        
        except Exception as e:
            print(f"Ошибка при выполнении действия: {e}")
            return False
    
    def _ask_gpt(self, query):
        """
        Отправка запроса к GPT и озвучивание ответа.
        
        Args:
            query (str): Запрос пользователя
        """
        try:
            print(f"Отправка запроса в GPT: {query}")
            
            # Вызов API OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # или "gpt-4" для более сложных запросов
                messages=[
                    {"role": "system", "content": "Ты - голосовой ассистент, который отвечает кратко и по делу. Ты работаешь с программистом и должен давать точные технические ответы."},
                    {"role": "user", "content": query}
                ],
                max_tokens=500
            )
            
            # Получение ответа
            answer = response.choices[0].message.content.strip()
            print(f"Ответ GPT: {answer}")
            
            # Вывод ответа на экран и озвучивание
            print("-" * 50)
            print(answer)
            print("-" * 50)
            self.speak(answer)
            
        except Exception as e:
            error_msg = f"Ошибка при обращении к GPT: {e}"
            print(error_msg)
            
            if "quota" in str(e) or "billing" in str(e):
                quota_message = "Превышен лимит API OpenAI. Пожалуйста, проверьте ваш тарифный план или платежные данные на сайте OpenAI."
                print(quota_message)
                self.speak(quota_message)
            else:
                self.speak("Произошла ошибка при обращении к ИИ")
    
    def speak(self, text):
        """
        Озвучивание текста.
        
        Args:
            text (str): Текст для озвучивания
        """
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    def add_new_command(self, trigger, action):
        """
        Добавление новой команды в конфигурацию.
        
        Args:
            trigger (str): Текст команды для распознавания
            action (str): Действие для выполнения
            
        Returns:
            bool: True, если команда добавлена успешно
        """
        try:
            # Добавляем новую команду в список
            self.commands.append({
                "trigger": trigger,
                "action": action
            })
            
            # Сохраняем обновленную конфигурацию в файл
            with open(self.config_file, 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=2)
            
            print(f"Добавлена новая команда: {trigger} -> {action}")
            return True
            
        except Exception as e:
            print(f"Ошибка при добавлении команды: {e}")
            return False


# Пример использования
if __name__ == "__main__":
    executor = CommandExecutor()
    # Тестирование обработки команды
    executor.process_command("открой хром")
    # Тестирование запроса к GPT
    executor.process_command("спроси у GPT как работает цикл событий в JavaScript") 