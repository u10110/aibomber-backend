import os
import ollama
from ollama import Client
from apps.home.models import Chat, Project, ProjectFile, ClientSettings, ChatMessages
import re
import random
from django.shortcuts import get_object_or_404
from decouple import config
from loguru import logger
from urllib.request import urlopen
import pybase64

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
import pandas as pd
import numpy as np

OPENAI_API_KEY = config("OPENAI_API_KEY")

client = Client(
    host='http://localhost:11434/'
)


def create_message_embedding(message_text):
    return ollama.embeddings(model='nomic-embed-text', prompt=message_text).embedding

def create_message_pca_embedding(messages):
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(messages)

    n_samples, n_features = X.shape
    n_components = min(n_samples, n_features)
    print(n_samples, n_features )
    # Применение PCA
    pca = PCA(n_components=5)  # Например, 2 главных компоненты
    pca.fit(X)
    ret =  pca.transform(X)
    feature_names = vectorizer.get_feature_names_out()

    for i in range(ret.shape[1]):
        print(f"Главная компонента {i+1}:")
        for word in feature_names:
            index = np.where(feature_names == word)

            print(f"  {word}: {ret[0, i] * vectorizer.idf_[index]}")
    return ret


def just_ask_question(question=None, photo=None):

    if photo is not None:
        photo_base64 = urlopen(photo).read()
        print(photo)
        messages = [
            {"role": "user", "content": question,  "images": [photo_base64]}
        ]
    else:
        messages =[
            {"role": "user", "content": question}
        ]

    response = client.chat(
        model='gemma3:4b',
        messages=messages,
        options={"temperature": 0.9}
    )

    answer = response.message.content
    return answer


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
        logger.info(f"projectisis {self.project}")
        if self.project.id:
            self.client_id = self.project.client_id
        logger.info(f"client_id {self.client_id}")
        
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
        cost_per_token = 0.00003  # Пример: $0.00002 за токен (замените на актуальное значение)
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
                raise ValueError(f"Недостаточно средств на балансе клиента {client_settings.client.phone}.")
            
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
        logger.debug(self.chat_id)
        chat = Chat.objects.filter(id=self.chat_id).first()

        if chat:
            self.is_auto_active = chat.is_auto_active
            chat_records = ChatMessages.objects.filter(chat_id=chat).order_by("created_at")
        else:
            chat_records = []

        if chat_records:
            self.chat_history = [
                {"role": "user", "content": record.user_message} if record.message_type == "incoming" else
                {"role": "assistant", "content": record.user_message}
                for record in chat_records
            ]
            self.chat_history.pop()
        else:
            self.chat_history = []

    def _load_knowledge_base(self):
        """
        Загружает базу знаний из текста и файлов.
        """
        #print(f"know {self.project.knowledge_base_text}")
        if self.project.knowledge_base_text:
            self.knowledge_texts.append(self.project.knowledge_base_text)


        project_files = ProjectFile.objects.filter(project=self.project)
        for project_file in project_files:
            # Выполняем обработку файла в зависимости от его расширения
            self.knowledge_texts += project_file.file_text

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

    def ask_question(self, question=None, photo=None, save_to_db=True):
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

        full_context = f"{self.project.prompt}\n\n" + "\n".join(self.knowledge_texts)


        if photo is not None:
            photo_base64 = urlopen(photo).read()

            full_context += '\r\nПерсонализированными сообшения  под характер человека на фото, если он там есть.' \
                            'Не учитывай обстановку и окружение на фото, в ответах используй только характеристики ' \
                            'личности.\r\n '

            messages = [{"role": "system", "content": full_context}] + self.chat_history + [
                {"role": "user", "content": question,  "images": [photo_base64]}
            ]
        else:
            messages = [{"role": "system", "content": full_context}] + self.chat_history + [
                {"role": "user", "content": question}
            ]

        #print(f"messages {messages}")

        # Отправляем запрос в OpenAI API
        try:

            response = client.chat(
                model='gemma3:4b',
                messages=messages,
                options={"temperature": 0.5}
            )
            answer = response.message.content


            #token_usage = response.usage.total_tokens
            # Вычисляем стоимость
            #cost = self._calculate_cost(token_usage)
            # Обновляем баланс пользователя
            #if self.client_id:
            #    self._update_user_balance(cost)

            if save_to_db:
                self._save_to_db(answer, question)

            return answer
        except Exception as e:
            # Обработка ошибок
            logger.error(f"Ошибка: {type(e).__name__}: {e}")
            return f"Ошибка: {str(e)}"
       

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

        #chat = Chat.objects.filter(id=self.chat_id).first()
        #if not ChatMessages.objects.filter(
        #    chat_id=chat,
        #    user_message=message_question
        #).exists():
        #    ChatMessages.objects.create(
        #        chat_id=chat,
        #        message_type="outcoming",
        #        user_name=self.channel_phone,
        #        user_message=message_question,
        #    )
        #else:
        #    return False
        return True


    def _get_gpt_version(self):
        """
        Возвращает версию GPT для использования.
        """
        return 'gemma3:4b'
        if self.project.gpt_version == 1:
            return "gpt-4o"
        elif self.project.gpt_version == 2:
            return "gpt-4o-mini"
        else:
            return "gpt-3.5-turbo"

    def ask_chat_status(self):

        question = "На каком их этапе из нижеперечисленных находится общение в  предыдущих сообщениях? Ведетя упещный диалог (success); Получен номер телефона или другой личный контакт для связи (contact_received); " \
                   "Проявлен интерес к  продукту (interest_shown), Предложение проигнорировали (closed). Ответь только соответствующим кодом из скобок. "

        messages = self.chat_history + [
            {"role": "user", "content": question}
        ]

        # Отправляем запрос в OpenAI API
        try:
            response = client.chat(
                model='gemma3:4b',
                messages=messages
            )
            answer = response.message.content.replace('(', '').replace(')', '')
        except Exception as e:
            # Обработка ошибок
            logger.error(f"Ошибка API OpenAI: {type(e).__name__}: {e}")
            return f"Ошибка OpenAI API: {str(e)}"

        return answer



