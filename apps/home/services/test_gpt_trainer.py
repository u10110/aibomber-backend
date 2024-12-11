import os
from datetime import datetime

# Импорт вашего класса GPTAssistant
from apps.home.services.gpt_assistant import GPTAssistant

# Моделируем Project как простой класс для тестирования
class Project:
    def __init__(self, id, client, title, prompt, knowledge_base_text=None, file=None, gpt_version=1):
        self.id = id
        self.client = client
        self.title = title
        self.prompt = prompt
        self.knowledge_base_text = knowledge_base_text
        self.file = file
        self.gpt_version = gpt_version

# Создаём тестовые данные
test_project = Project(
    id=1,
    client="Test User",
    title="Помощник elimentio",
    prompt="ты пытаешься увлечь пользователя купить продукт",
    knowledge_base_text="магазин игрушек Ellementio, игрушки синие по 200р, красные по 100р",
    file=None,  # Можно указать путь к файлу, если нужно
    gpt_version=1
)

# Инициализация ассистента
assistant = GPTAssistant(test_project)

# Тестируем загрузку базы знаний
print("=== Тест загрузки базы знаний ===")
if assistant.vectorstore:
    print("База знаний успешно загружена.")
else:
    print("Ошибка загрузки базы знаний.")

# Тестируем задавание вопросов
print("\n=== Тест вопроса к ассистенту ===")
try:
    question = "Что ты можешь рассказать о своей базе знаний?"
    response = assistant.ask_question(question)
    print(f"Вопрос: {question}")
    print(f"Ответ: {response}")
except Exception as e:
    print(f"Ошибка при обработке вопроса: {e}")

# Тестируем сохранение состояния
print("\n=== Тест сохранения состояния ===")
assistant.save_assistant_state()
state_file = f"assistant_state_{test_project.id}.json"
if os.path.exists(state_file):
    print(f"Состояние успешно сохранено в {state_file}.")
else:
    print("Ошибка при сохранении состояния.")

# Тестируем загрузку состояния
print("\n=== Тест загрузки состояния ===")
assistant.load_assistant_state()
if assistant.chat_history:
    print("Состояние успешно загружено.")
    print("История чата:", assistant.chat_history)
else:
    print("Ошибка при загрузке состояния.")
