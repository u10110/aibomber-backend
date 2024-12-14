import os
from openai import OpenAI
from datetime import datetime
from apps.home.models import Chat
from PyPDF2 import PdfReader
from docx import Document


OPENAI_API_KEY="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"
client = OpenAI(
    api_key=OPENAI_API_KEY  # Рекомендуется использовать переменные окружения
)
class GPTAssistant:
    def __init__(self, project, user_id=None):
        """
        Инициализация ассистента на основе данных проекта.
        :param project: Экземпляр модели Project.
        """
        self.project = project
        self.user_id = user_id
        self.chat_history = []  # Здесь хранится история в формате [{"role": "user", ...}, {"role": "assistant", ...}]
        self.knowledge_texts = []  # Здесь хранится база знаний
        
        if user_id:
            self._load_chat_history()
        self._load_knowledge_base()

    def _load_chat_history(self):
        """
        Загружает историю чата из базы данных на основе user_id.
        """
        chat_records = Chat.objects.filter(project=self.project, user_id=self.user_id).order_by("created_at")
        self.chat_history = [
            {"role": "user", "content": record.user_message} if record.message_type == "message" else 
            {"role": "assistant", "content": record.user_message}
            for record in chat_records
        ]

    def _load_knowledge_base(self):
        """
        Загружает базу знаний из текста и файлов.
        """
        if self.project.knowledge_base_text:
            self.knowledge_texts.append(self.project.knowledge_base_text)

        if self.project.file:
            file_path = self.project.file.path
            ext = os.path.splitext(file_path)[1].lower()
            self.knowledge_texts += self._extract_text_from_file(file_path, ext)

    @staticmethod
    def _extract_text_from_file(file_path, ext):
        """
        Извлекает текст из файлов различных форматов.
        """
        try:
            if ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    return [f.read()]
            elif ext == ".pdf":
                reader = PdfReader(file_path)
                return [page.extract_text() for page in reader.pages]
            elif ext == ".docx":
                doc = Document(file_path)
                return [p.text for p in doc.paragraphs]
            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            print(f"Error extracting text from file {file_path}: {e}")
            return []

    def ask_question(self, question, save_to_db=True):
        """
        Задает вопрос ассистенту, используя OpenAI API.
        """
        # Формируем контекст для запроса
        full_context = f"{self.project.prompt}\n\n" + "\n".join(self.knowledge_texts)
        messages = [{"role": "system", "content": full_context}] + self.chat_history + [
            {"role": "user", "content": question}
        ]

        # Отправляем запрос в OpenAI API
        try:
            response = client.chat.completions.create(
                model=self._get_gpt_version(),  # Версия GPT: "gpt-4o" или "gpt-3.5-turbo"
                messages=messages,
                temperature=0.7  # Регулирует креативность ответов
            )
            answer = response.choices[0].message.content
            self._update_chat_history(question, answer)

            if save_to_db:
                self._save_to_db(question, answer)

            return answer
        except Exception as e:
            # Обработка ошибок
            print(f"Ошибка API OpenAI: {type(e).__name__}: {e}")
            return f"Ошибка OpenAI API: {str(e)}"


    
       

    def _update_chat_history(self, question, response):
        """
        Обновляет историю чата.
        """
        self.chat_history.append({"role": "user", "content": question})
        self.chat_history.append({"role": "assistant", "content": response})

    def _save_to_db(self, question, response):
        """
        Сохраняет новый вопрос-ответ в базу данных.
        """
        Chat.objects.create(
            project=self.project,
            client=self.project.client,
            user_id=self.user_id,
            message_type="message",
            user_name=self.project.client.username,
            user_message=question,
        )
        Chat.objects.create(
            project=self.project,
            client=self.project.client,
            user_id=self.user_id,
            message_type="anwser",
            user_name="GPT Assistant",
            user_message=response,
        )

    def _get_gpt_version(self):
        """
        Возвращает версию GPT для использования.
        """
        return "gpt-4" if self.project.gpt_version == 1 else "gpt-3.5-turbo"
