import os
import json
from datetime import datetime
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from apps.home.models import Chat

from PyPDF2 import PdfReader  # Для чтения PDF-файлов
from docx import Document  # Для чтения DOCX-файлов
from apps.home.models import Project  # Если Project используется для связи
import os


import logging

# Настраиваем логирование
logging.basicConfig(level=logging.DEBUG)

# Включаем логи для langchain
logger = logging.getLogger("langchain")
logger.setLevel(logging.DEBUG)

print(f"Текущий уровень логирования: {logging.getLevelName(logger.level)}")


OPENAI_API_KEY="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"
if not OPENAI_API_KEY:
    print("OPENAI_API_KEY не установлен!")

class GPTAssistant:
    def __init__(self, project, user_id=None):
        """
        Инициализация ассистента на основе данных проекта.
        :param project: Экземпляр модели Project.
        """
        print(OPENAI_API_KEY)
        self.project = project
        self.user_id = user_id
        self.vectorstore = None
        self.chat_history = []
        if user_id:
            self._load_chat_history()
        self._load_knowledge_base()

    def _load_chat_history(self):
        """
        Загружает историю чата из базы данных на основе user_id и форматирует её.
        """
        chat_records = Chat.objects.filter(project=self.project, user_id=self.user_id).order_by("created_at")
        self.chat_history = []
        for record in chat_records:
            if record.message_type == "anwser":
                self.chat_history.append((record.user_message, record.user_message))


    def _load_knowledge_base(self):
        """
        Загружает и индексирует базу знаний из текста и файлов.
        """
        knowledge_texts = []

        # Загружаем текст базы знаний
        if self.project.knowledge_base_text:
            knowledge_texts.append(self.project.knowledge_base_text)

        # Загружаем файл базы знаний
        if self.project.file:
            file_path = self.project.file.path
            ext = os.path.splitext(file_path)[1].lower()
            knowledge_texts += self._extract_text_from_file(file_path, ext)

        if knowledge_texts:
            try:
                logger.debug(f"Начинаем создание эмбеддингов для текстов: {knowledge_texts}")
                embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
                logger.debug("Эмбеддинги успешно созданы.")
                
                logger.debug("Начинаем индексирование текстов в FAISS.")
                self.vectorstore = FAISS.from_texts(knowledge_texts, embeddings)
                logger.debug("Индексирование в FAISS завершено.")
            except Exception as e:
                logger.error(f"Ошибка при создании эмбеддингов или индексации в FAISS: {e}")
                raise

    def test_retrieval(self, query):
        """
        Тестирует поиск в базе знаний.
        """
        if not self.vectorstore:
            raise ValueError("База знаний не загружена.")
        
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        results = retriever.get_relevant_documents(query)
        print("Результаты поиска:", results)
        return results

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
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                return [page.extract_text() for page in reader.pages]
            elif ext in [".docx"]:
                from docx import Document
                doc = Document(file_path)
                return [p.text for p in doc.paragraphs]
            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            print(f"Error extracting text from file {file_path}: {e}")
            return []

    def ask_question(self, question, save_to_db=True):
        """
        Задает вопрос ассистенту, учитывая историю переписки и prompt. 
        Использование базы знаний (vectorstore) опционально.
        """
        # Проверяем, задан ли prompt
        if not self.project.prompt:
            print("Промпт не задан.")
            raise ValueError("Промпт не задан.")

        print(f"gpt version: {self.project.gpt_version}")

        # Инициализируем модель
        llm = ChatOpenAI(
            temperature=0,
            model=self._get_gpt_version(),
            openai_api_key=OPENAI_API_KEY,
            verbose=True
        )
        print(llm)
        print("message here")

        # Формируем полный контекст (с prompt)
        full_context = f"{self.project.prompt}\n\n{question}"

        # Если база знаний доступна, используем retriever
        if self.vectorstore:
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
            qa_chain = ConversationalRetrievalChain.from_llm(llm, retriever)
            response = qa_chain({"question": full_context, "chat_history": self.chat_history})
            answer = response["answer"]
        else:
            # Если база знаний недоступна, отправляем только full_context
            answer = llm(full_context).content

        # Обновляем историю чата
        self._update_chat_history(question, answer)

        if save_to_db:
            self._save_to_db(question, answer)

        return answer




    def _update_chat_history(self, question, response):
        """
        Обновляет историю чата.
        """
        self.chat_history.append({"question": question, "response": response})

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
        if self.project.gpt_version == 1:
            return "gpt-4"
        elif self.project.gpt_version == 2:
            return "gpt-3.5-turbo"
        else:
            raise ValueError("Invalid GPT version")

