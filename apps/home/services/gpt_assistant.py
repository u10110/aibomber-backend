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

openai_api_key = os.getenv("OPENAI_API_KEY")


class GPTAssistant:
    def __init__(self, project, user_id):
        """
        Инициализация ассистента на основе данных проекта.
        :param project: Экземпляр модели Project.
        """
        self.project = project
        self.user_id = user_id
        self.vectorstore = None
        self.chat_history = []
        self._load_chat_history()
        self._load_knowledge_base()

    def _load_chat_history(self, ):
        """
        Загружает историю чата из базы данных на основе user_id.
        
        :param user_id: Идентификатор пользователя.
        """
        chat_records = Chat.objects.filter(project=self.project, user_id=self.user_id).order_by("created_at")
        self.chat_history = [
            {"question": record.user_message, "response": record.user_message}
            for record in chat_records
            if record.message_type == "anwser"
        ]

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
            embeddings = OpenAIEmbeddings()
            self.vectorstore = FAISS.from_texts(knowledge_texts, embeddings)

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

    def ask_question(self, question):
        """
        Задает вопрос ассистенту, учитывая историю переписки.
        """
        if not self.vectorstore:
            raise ValueError("Knowledge base is not loaded or empty.")


        llm = ChatOpenAI(
            temperature=0, 
            model=self._get_gpt_version(), 
            openai_api_key=openai_api_key
        )
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        qa_chain = ConversationalRetrievalChain.from_llm(llm, retriever)

        response = qa_chain({"question": question, "chat_history": self.chat_history})
        self._update_chat_history(question, response["answer"])
        self._save_to_db(question, response["answer"])

        return response["answer"]



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
            user_id=self.project.client.id,
            message_type="message",
            user_name=self.project.client.username,
            user_message=question,
        )
        Chat.objects.create(
            project=self.project,
            client=self.project.client,
            user_id=self.project.client.id,
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

