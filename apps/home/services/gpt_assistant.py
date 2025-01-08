import os
from openai import OpenAI
from datetime import datetime
from apps.home.models import Chat, Project, ProjectFile, ClientSettings, ChatMessages
from PyPDF2 import PdfReader
from docx import Document
import re
import random
from django.shortcuts import get_object_or_404


OPENAI_API_KEY="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"
client = OpenAI(
    api_key=OPENAI_API_KEY  # Рекомендуется использовать переменные окружения
)
class GPTAssistant:
    def __init__(self, project, chat_id=None, channel_phone=None, user_id=None,):
        """
        Инициализация ассистента на основе данных проекта.
        :param project: Экземпляр модели Project.
        """
        self.project = project
        self.chat_id = chat_id
        self.is_auto_active = True
        self.client_id = None
        print(f"projectisis {self.project}")
        if self.project.id:
            self.client_id = self.project.client_id
        print(f"client_id {self.client_id}")
        
        self.channel_phone=channel_phone
        self.user_id=user_id
        
        self.chat_history = []  # Здесь хранится история в формате [{"role": "user", ...}, {"role": "assistant", ...}]
        self.knowledge_texts = []  # Здесь хранится база знаний
        
        if chat_id:
            self._load_chat_history()
        self._load_knowledge_base()

    def _calculate_cost(self, token_usage):
        """
        Вычисляет стоимость запроса на основе использования токенов.
        """
        cost_per_token = 0.00002  # Пример: $0.00002 за токен (замените на актуальное значение)
        return token_usage * cost_per_token


    def _update_user_balance(self, cost):
        """
        Уменьшает баланс в ClientSettings по client_id.
        """
        try:
            print(self.client_id)
            client_settings = ClientSettings.objects.get(client_id=self.client_id)
            # Проверка на достаточность баланса
            if client_settings.balance < cost:
                raise ValueError("Недостаточно средств на балансе.")
            
            # Уменьшение баланса
            client_settings.balance -= cost
            client_settings.save()

            return client_settings.balance
        except ClientSettings.DoesNotExist:
            raise ValueError(f"ClientSettings with client_id {self.client_id} does not exist.")



    def _load_chat_history(self):
        """
        Загружает историю чата из базы данных на основе user_id.
        """
        print(self.chat_id)
        chat = Chat.objects.filter(id=self.chat_id).first()

        if chat:
            self.is_auto_active = chat.is_auto_active
            chat_records = ChatMessages.objects.filter(chat_id=chat.id).order_by("created_at")
        else:
            chat_records = []

        if chat_records:
            self.chat_history = [
                {"role": "user", "content": record.user_message} if record.message_type == "message" else 
                {"role": "assistant", "content": record.user_message}
                for record in chat_records
            ]
        else:
            self.chat_history = []

    def _load_knowledge_base(self):
        """
        Загружает базу знаний из текста и файлов.
        """
        print(f"know {self.project.knowledge_base_text}")
        if self.project.knowledge_base_text:
            self.knowledge_texts.append(self.project.knowledge_base_text)


        project_files = ProjectFile.objects.filter(project=self.project)
        for project_file in project_files:
            file_path = project_file.file.path
            ext = os.path.splitext(file_path)[1].lower()

            # Выполняем обработку файла в зависимости от его расширения
            self.knowledge_texts += self._extract_text_from_file(file_path, ext)
        print(self.knowledge_texts)


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

    def _process_spintax(self, text):
        """
        Обрабатывает спинтакс-строку и возвращает случайный вариант.
        """
        while '{' in text and '}' in text:
            text = re.sub(
                r'\{([^{}]*)\}',
                lambda match: random.choice(match.group(1).split('|')),
                text
            )
        return text

    def ask_question(self, question=None, save_to_db=True):
        """
        Задает вопрос ассистенту, используя OpenAI API.
        """
        # Формируем контекст для запроса
        if not self.is_auto_active:
            self._save_to_db(question)
        
        if not question and self.project.hello_text:
            hello_message = self._process_spintax(self.project.hello_text)
            r = self._save_to_db(hello_message)
            if r:
                return hello_message
            else:
                return {"status": "уже отправляли хелоу", "anwser": ""}



        if not question:
            try:
                messages = [
                    {"role": "system", "content": full_context},  # Приветственное сообщение на основе промпта
                    {"role": "user", "content": "Привет, расскажи о себе."},  # Типичный запрос для генерации приветствия
                ]

                response = client.chat.completions.create(
                    model=self._get_gpt_version(),  # Версия GPT: "gpt-4o" или "gpt-3.5-turbo"
                    messages=messages,
                    temperature=0.7  # Регулирует креативность ответов
                )
                answer = response.choices[0].message.content
                
                token_usage = response.usage.total_tokens
                # Вычисляем стоимость
                cost = self._calculate_cost(token_usage)
                # Обновляем баланс пользователя
                if self.client_id:
                    self._update_user_balance(cost)
                
            
                self._save_to_db(answer)
                return response.choices[0].message.content
            except Exception as e:
                print(f"Ошибка API OpenAI: {type(e).__name__}: {e}")
                return f"Ошибка OpenAI API: {str(e)}"

        full_context = f"{self.project.prompt}\n\n" + "\n".join(self.knowledge_texts)
        messages = [{"role": "system", "content": full_context}] + self.chat_history + [
            {"role": "user", "content": question}
        ]
        print(f"messages {messages}")

        # Отправляем запрос в OpenAI API
        try:
            response = client.chat.completions.create(
                model=self._get_gpt_version(),  # Версия GPT: "gpt-4o" или "gpt-3.5-turbo"
                messages=messages,
                temperature=0.7  # Регулирует креативность ответов
            )
            answer = response.choices[0].message.content
            
            self._update_chat_history(question, answer)
            
            token_usage = response.usage.total_tokens
            # Вычисляем стоимость
            cost = self._calculate_cost(token_usage)
            # Обновляем баланс пользователя
            if self.client_id:
                self._update_user_balance(cost)
            

            if save_to_db:
                self._save_to_db(answer, question)

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

    def _save_to_db(self, message_question, anwser_response=None):
        """
        Сохраняет новый вопрос-ответ в базу данных.
        """

        chat = Chat.objects.filter(id=self.chat_id).first()
        if not ChatMessages.objects.filter(
            chat_id=chat,
            user_message=message_question
        ).exists():
            print(11111111111111)
            print(self.project.client)
            ChatMessages.objects.create(
                chat_id=chat,
                message_type="anwser",
                user_name=self.channel_phone,
                user_message=message_question,
            )
        else:
            return False
        return True


    def _get_gpt_version(self):
        """
        Возвращает версию GPT для использования.
        """
        if self.project.gpt_version == 1:
            return "gpt-4o"
        elif self.project.gpt_version == 2:
            return "gpt-4o-mini"
        else:
            return "gpt-3.5-turbo"
