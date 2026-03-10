
import string
from decouple import config
from sqlite3 import IntegrityError
import traceback
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.files.storage import FileSystemStorage
from django.db.utils import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template import loader
from django.urls import path, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DeleteView
from loguru import logger
from lxml import html
from sentry_sdk import last_event_id
import re


from apps.authentication.models import UserInfo


from core.settings import MEDIA_ROOT


from apps.telegram.sndr import ProjectProcessor
from apps.telegram.prsr import process_project


from .helper import Helper
from .models import (
    ReferralClickCounter,
    ReferralUsers,
    ReferralLinks,
    ClientSettings,
    Channel,
    Chat,
    Phone,
    ChatMessages
)

from .services.services import MinioService
from django.shortcuts import get_object_or_404
from django.db.models import Max, OuterRef, Subquery, Count, Q, F
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

from django.shortcuts import render
from django.http import JsonResponse
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from .models import Project
from .services.gpt_assistant import GPTAssistant
from django.db.models import Count, Max, Subquery, OuterRef, IntegerField, Case, When
import random


TELETHON_HOST = config("TELETHON_HOST")
WHATSAPPJS_HOST = config('WHATSAPPJS_HOST')

def error(request):
    return render(request, "errors/technical_break.html")


def dynamic_page(request, page_name):
    return render(request, f'home/{page_name}.html')


def password_update(request):
    if request.method == "POST":
        data = request.POST
        print(data)
        user = request.user
        if user.check_password(data["password-current"]):
            if data["password-new"] == data["password-confirm"]:
                user.set_password(data["password-new"])
                user.save()
                update_session_auth_hash(request, user)
                return JsonResponse({"resp": "ok"}, status=200)
            else:
                return JsonResponse({"resp": "password not mutch"}, status=200)
        else:
            return JsonResponse({"resp": "bad password"}, status=200)




def set_bad_payed(request):
    date_now = datetime.datetime.now(datetime.timezone.utc)
    products = ProductBuyout.objects.filter(
        client_id=request.user, payment_status="pay_await", status="active"
    )
    for product in products:
        if (product.pay_link_generated + timedelta(seconds=300)) < date_now:
            ProductBuyout.objects.filter(id=product.id).update(payment_status="bad_pay")
            # limits = Limits.objects.get(
            #     client_id=request.user, start_date__lte=date_now, end_date__gte=date_now
            # )
            # limits.buyout_limit += 1
            # limits.save()
    return JsonResponse({"resp": True})




def set_sms_type(request):
    if request.method == "POST":
        num_group = request.POST["num_group"]
        sms_type = request.POST["sms_type"]
        print(sms_type)
        start_time = None
        end_time = None
        if sms_type == "tg" or sms_type == "tgsbp":
            start_time = request.POST["start_time"]
            end_time = request.POST["end_time"]
        ProductBuyout.objects.filter(
            client_id=request.user.id, num_group=num_group
        ).update(pay_type=sms_type, tg_start_date=start_time, tg_end_date=end_time)
    return JsonResponse({"resp": "ok"}, status="200")




def review_rating(request):
    pass




def auto_pay_stop(request, group):
    logged_in_user = request.user
    ProductBuyout.objects.filter(client_id=logged_in_user.id).filter(
        num_group=group
    ).update(pay_type="no")
    return HttpResponseRedirect(f"/buyout?status=active&group={group}")


def index(request):
    print(Helper.get_client_ip(request))
    return HttpResponseRedirect(reverse('projects'))


def add_sms_cloud(request):
    logged_in_user = request.user
    if request.method == "POST":
        form = ClientSettingsForm(request.POST)
        if form.is_valid():
            data = {
                "sms_cloud": form.cleaned_data.get("sms_cloud"),
            }
            print(data)
            new_sms_cloud = ClientSettings.objects.update_or_create(
                {"sms_cloud": data["sms_cloud"], "client_id": logged_in_user.id},
                client_id=logged_in_user.id,
            )
        else:
            context = {}
            context["error"] = True
            context["error_message"] = "Неверная ссылка на облако"
            return render(request, "apps/add-card.html", context)
    return HttpResponseRedirect("/add-card/")


def get_tochka_phone(request):
    logged_in_user = request.user
    if request.method == "POST":
        usage_phones = {}
        for i in TochkaNumbers.objects.all():
            usage_phones[i.id] = 0
        for i in ClientSettings.objects.all():
            if i.tochka_number:
                usage_phones[i.tochka_number.id] += 1
        common_value = sorted(usage_phones, key=usage_phones.get)[0]
        cs = ClientSettings.objects.get(client=logged_in_user)
        tn = TochkaNumbers.objects.get(id=common_value)
        cs.tochka_number = tn
        cs.save()
    return HttpResponseRedirect("/add-card/")


def card_delete(request, pk):
    ClientCard.objects.filter(id=pk, client=request.user.id).delete()
    return HttpResponseRedirect("/add-card/")




def get_segment(request):
    try:

        segment = request.path.split("/")[-1]
        active_menu = None

        if segment == "" or segment == "index.html":
            segment = "index"
            active_menu = "dashboard"

        if segment.startswith("dashboards-"):
            active_menu = "dashboard"

        if (
                segment.startswith("account-")
                or segment.startswith("users-")
                or segment.startswith("profile-")
                or segment.startswith("projects-")
        ):
            active_menu = "pages"

        if (
                segment.startswith("notifications")
                or segment.startswith("sweet-alerts")
                or segment.startswith("charts.html")
                or segment.startswith("widgets")
                or segment.startswith("pricing")
        ):
            active_menu = "pages"

        return segment, active_menu

    except:
        return "index", "dashboard"





@csrf_exempt
def toggle_project_active(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')
            is_active = data.get('is_active')

            project = Project.objects.get(id=project_id, client=request.user)
            project.is_active = is_active
            if is_active:
                project.status = 'active'
            else:
                project.status = 'paused'
            project.save()

            return JsonResponse({'success': True,
                                 'message': 'Состояние обновлено',
                                 'is_active': project.is_active,
                                 'status': project.status})

        except Project.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Проект не найден'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Неверный метод запроса'}, status=400)


def project_start(request, pk):
    project = get_object_or_404(Project, pk=pk, client=request.user)
    project.status = "active"  # Укажите соответствующее значение
    project.is_active = True
    project.save()
    return redirect('projects')


def project_stop(request, pk):
    project = get_object_or_404(Project, pk=pk, client=request.user)
    project.status = "paused"  # Укажите соответствующее значение
    project.is_active = False
    project.save()
    return redirect('projects')


def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, client=request.user)
    Channel.objects.filter(project_id=project.id).update(project_id=None)
    Recipient.objects.filter(project_id=project.id).update(project_id=None)
    project.delete()
    return redirect('projects')


def channel_start(request, pk):
    project = get_object_or_404(Channel, pk=pk, client=request.user)
    project.status = "active"  # Укажите соответствующее значение
    project.save()
    return redirect('channels')


def channel_stop(request, pk):
    project = get_object_or_404(Channel, pk=pk, client=request.user)
    project.status = "stopped"  # Укажите соответствующее значение
    project.save()
    return redirect('channels')


def channel_delete(request, pk):
    project = get_object_or_404(Channel, pk=pk, client=request.user)
    project.delete()
    return redirect('channels')


@csrf_exempt
def toggle_channel_active(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        channel_id = data.get('channel_id')
        is_active = data.get('is_active')

        try:
            channel = Channel.objects.get(id=channel_id)
            channel.is_active = is_active
            channel.save()
            return JsonResponse({'success': True, 'channel_id': channel_id, 'is_active': is_active})
        except Channel.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Channel not found'}, status=404)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def list_recipient_edit(request, id):
    recipient = get_object_or_404(Recipient, id=id, client=request.user)

    if request.method == 'POST':
        form = RecipientForm(request.POST, instance=recipient)
        print(f" form {form}")
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        return JsonResponse({'success': False, 'message': 'Неверный метод запроса'})



def list_recipient_delete(request, pk):
    list_recipient = get_object_or_404(Recipient, pk=pk, client=request.user)
    list_recipient.delete()
    return redirect('list-recipient')


def get_context_data(request, user_id=None, chats=None, messages=None, current_chat=None):
    projects = Project.objects.filter(client_id=request.user.id)

    context = {
        'chats': chats,
        'messages': messages,
        'chat': current_chat,
        'projects': projects,
    }
    return context


def chat(request):
    chat_id = request.GET.get('chat_id')
    user_id = request.user.id

    current_chat = Chat.objects.filter(
        id=chat_id
    ).first()

    chats = Chat.objects.filter(
        project__in=Project.objects.filter(client_id=request.user.id)
    )

    current_messages = []

    if chat:
        current_messages = ChatMessages.objects.filter(
            chat_id=chat_id,
        ).order_by('created_at')

    context = {
        'chats': chats,
        'messages': current_messages,
        'chat': current_chat,
        'projects': Project.objects.filter(client_id=user_id)
    }
    return render(request, "apps/chat.html", context)


def chat_messages(request):
    chat_id = request.GET.get('chat_id', None)
    user_id = request.GET.get('user_id', None)
    client_id = request.user.id

    if chat_id is not None:
        current_chat = Chat.objects.filter(id=chat_id).first()
    else:
        current_chat = None

    if request.method == "POST":
        user_message = request.POST.get('user_message')
        if user_message:

            if current_chat:
                user_id = current_chat.user_id
                if not current_chat.user_id.startsWith('@'):
                    user_id = '@' + user_id

                payload = json.dumps({
                    "phone": current_chat.channel.phone,
                    "username": user_id,
                    "message": user_message
                })
                headers = {
                    'Content-Type': 'application/json'
                }
                response = requests.post(
                    f"{TELETHON_HOST}/send-message/",
                    headers=headers,
                    data=payload
                )
                print(response.status_code, response.text)
                ChatMessages.objects.create(
                    chat_id=current_chat,
                    user_name=current_chat.user_name,
                    user_message=user_message,
                    message_type='outcoming',  # Изменено на 'question'
                )
            return redirect(f'{reverse("messages")}?chat_id={chat_id}')

    chats = Chat.objects.filter(
        project__in=Project.objects.filter(client_id=request.user.id)
    ).order_by('-last_message_time')

    messages = []

    if current_chat:
        messages = ChatMessages.objects.filter(
            chat_id=current_chat
        ).order_by('created_at')

    context = {
        'chats': chats,
        'messages': messages,
        'chat': current_chat,
        'projects': Project.objects.filter(client_id=client_id)
    }

    return render(request, 'apps/chat.html', context)


def channels(request):
    if request.method == 'POST':
        form = ChannelForm(request.POST, initial={'client': request.user})
        print(1)
        if form.is_valid():
            channels = form.save()  # Сохраняем все записи
            return redirect('/channels/')
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)


    else:
        form = ChannelForm(request.POST, initial={'client': request.user})

    # Получаем все проекты из модели
    projects = Channel.objects.filter(client=request.user)

    project_titles = {project.id: project.title for project in Project.objects.filter(client=request.user)}

    # Добавляем название проекта к каждому каналу
    for channel in projects:
        channel.project_title = project_titles.get(channel.project_id, "Не привязан")

    # Передаем данные в шаблон
    context = {
        'form': form,
        'channels': projects,
    }
    return render(request, 'apps/channels.html', context)


BASE_URL = "https://my.telegram.org"


def create_app_internal(session):
    """
    Внутренняя функция для создания приложения.
    Используется из verify_code.
    """
    try:
        response = session.post(
            f"{BASE_URL}/apps/create",
            data={
                'app_title': 'Eliment',  # Название приложения
                'app_shortname': 'eliment_app',  # Уникальное имя
                'app_platform': 'desktop',  # Можно заменить на web/other
                'app_url': '',  # URL приложения, если есть
                'app_desc': '',  # Описание приложения
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if response.status_code == 200:
            response_data = response.json()
            return {
                'success': True,
                'api_id': response_data.get('api_id'),
                'api_hash': response_data.get('api_hash'),
            }
        else:
            return {
                'success': False,
                'error': 'Ошибка при создании приложения на стороне Telegram.',
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


@csrf_exempt
def create_app(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        app_title = data.get('title', 'eliment')
        app_shortname = data.get('shortname', 'eliment_app')

        try:
            # Извлекаем сохраненную сессию
            session = requests.Session()
            session.cookies.update(request.session.get('tg_session', {}))

            # Отправляем запрос на создание приложения
            response = session.post(
                f"{BASE_URL}/apps/create",
                data={
                    'app_title': app_title,
                    'app_shortname': app_shortname,
                    'app_platform': 'desktop',  # Можно заменить на web/other
                    'app_url': '',  # URL приложения, если есть
                    'app_desc': '',  # Описание приложения
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if response.status_code == 200:
                # Парсим `API_ID` и `API_HASH` из ответа
                api_id = response.json().get('api_id')
                api_hash = response.json().get('api_hash')
                return JsonResponse({'success': True, 'api_id': api_id, 'api_hash': api_hash})
            else:
                return JsonResponse({'success': False, 'error': 'Ошибка при создании приложения.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': ''})



@csrf_exempt
def toggle_auto_active(request, chat_id):
    if request.method == 'POST':
        try:
            # Получаем данные из тела запроса
            data = json.loads(request.body)
            is_auto_active = data.get('is_auto_active')

            if is_auto_active is None:
                return JsonResponse({'error': 'is_auto_active is required'}, status=400)

            # Получаем объекты Chat и TgID
            chat = get_object_or_404(Chat, id=chat_id)

            chat.is_auto_active = is_auto_active
            chat.save()

            return JsonResponse({'is_auto_active': chat.is_auto_active})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def change_status(request, chat_id):
    client_id = request.user.id
    if request.method == 'POST':
        data = json.loads(request.body)
        new_status = data.get('status')

        chat = Chat.objects.get(id=chat_id)
        if chat and chat.project.client.id == client_id:
            if new_status == 'deleted':
                chat.status = new_status
                chat.delete()
            else:
                chat.status = new_status
                chat.save()

        # tg_id = TgID.objects.get(tg_id=chat.user_id)
        # tg_id.status = new_status
        # tg_id.save()

        return JsonResponse({'status': chat.status})
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def send_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone')

            if not phone_number:
                return JsonResponse({"message": "Номер телефона не указан", "success": False})

            phone_number = re.sub(r'[^\d+]', '', phone_number.strip())
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number  # Добавляем '+' в начало, если его нет
            channel, created = Channel.objects.get_or_create(phone=phone_number, client=request.user)

            if channel.source == 'telegram':
                response = requests.post(
                    f"{TELETHON_HOST}/send-code/",
                    params={"phone": phone_number},
                )
                logger.debug(response)
                if response.status_code == 200:
                    return JsonResponse(response.json())
                else:
                    return JsonResponse({"message": response.text, "success": False})

            if channel.source == 'whatsapp':
                response = requests.post(
                    f"{WHATSAPPJS_HOST}/send-code/",
                    params={"phone": phone_number},
                )
                logger.debug(response.content)
                if response.status_code == 200:
                    return JsonResponse(response.json())
                else:
                    return JsonResponse({"message": response.text, "success": False})

        except Exception as e:
            logger.error(traceback.format_exc())
            return JsonResponse({"message": str(e), "success": False})

    return JsonResponse({"message": "Метод запроса должен быть POST", "success": False})


@csrf_exempt
def is_auth(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone')

            if not phone_number:
                return JsonResponse({"message": "Номер телефона не указан", "success": False})

            phone_number = re.sub(r'[^\d+]', '', phone_number.strip())
            channel = Channel.objects.get(phone=phone_number, client=request.user)
            if channel.source == 'whatsapp':
                response = requests.get(
                    f"{WHATSAPPJS_HOST}/is-auth/",
                    params={"phone": phone_number},
                )
                logger.debug(response.content)
                if response.status_code == 200:
                    return JsonResponse(response.json())
                else:
                    return JsonResponse({"message": response.text, "success": False})

        except Exception as e:
            logger.error(traceback.format_exc())
            return JsonResponse({"message": str(e), "success": False})

    return JsonResponse({"message": "Метод запроса должен быть POST", "success": False})

# Шаг 2: Подтверждаем код авторизации
@csrf_exempt
def verify_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone')
            code = data.get('code')

            if not phone_number or not code:
                return JsonResponse({"message": "Номер телефона или код не предоставлены", "success": False})

            # Отправка запроса в FastAPI
            print({"phone": phone_number, "code": code})
            response = requests.post(
                f"{TELETHON_HOST}/verify-code/",
                json={"phone": phone_number, "code": code},
            )

            if response.status_code == 200:
                # Если успех, обновляем статус в базе данных
                channel, created = Channel.objects.get_or_create(phone=phone_number, client=request.user)
                channel.status = 'authorized'
                channel.save()

                return JsonResponse(response.json())
            else:
                return JsonResponse({"message": response.text, "success": False}, status=response.status_code)
        except Exception as e:
            logger.error(traceback.format_exc())
            return JsonResponse({"message": str(e), "success": False})

    return JsonResponse({"message": "Метод запроса должен быть POST", "success": False})


@csrf_exempt
def create_project_chat(request):
    """
    Обрабатывает запросы чата на этапе создания проекта.
    """
    if request.method == "POST":
        try:
            # Парсим данные формы
            data = json.loads(request.body)
            project = Project(
                id=None,
                title=data.get("title"),
                agent_type=data.get("agent_type"),
                work_option=data.get("work_option"),
                gpt_version=int(data.get("gpt_version")),
                knowledge_base_text=data.get("knowledge_base_text"),
                hello_text=data.get("hello_text"),
                prompt=data.get("prompt"),
            )

            # Форматируем историю чата
            chat_history = data.get("chat_history", [])
            formatted_history = []

            # Форматируем историю чата
            for item in chat_history:
                question = item.get("question")
                response = item.get("response")
                if question and response:  # Проверяем, что есть и вопрос, и ответ
                    formatted_history.append({"role": "user", "content": question})
                    formatted_history.append({"role": "assistant", "content": response})

            # Ограничиваем длину истории (например, 10 пар сообщений)
            formatted_history = formatted_history[-20:]  # 10 вопросов и 10 ответов

            # Инициализируем GPTAssistant с историей чата
            assistant = GPTAssistant(project)
            # Передаём историю в GPTAssistant
            assistant.chat_history = formatted_history

            # Получаем вопрос
            logger.debug(assistant.chat_history)
            question = data.get("question")
            if not question:
                return JsonResponse({"error": "Вопрос не предоставлен."}, status=400)
            logger.debug(question)
            # Получаем ответ от GPT
            response = assistant.ask_question(question, False)

            return JsonResponse({
                "question": question,
                "response": response
            }, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Метод не поддерживается."}, status=405)


@csrf_exempt
def gpt_assistant(request):
    """
    Эндпоинт для взаимодействия с GPTAssistant.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

    # Получение user_id, project_id и question из тела запроса
    chat_id = request.POST.get('chat_id')
    project_id = request.POST.get('project_id')
    question = request.POST.get('question')

    channel_phone = request.POST.get('channel_phone')
    user_id = request.POST.get('user_id')

    if not project_id:
        return JsonResponse({"error": "Missing required parameters: user_id, project_id, or question"}, status=400)

    # Получение объекта проекта
    project = get_object_or_404(Project, id=project_id)
    print(project)

    # Создание экземпляра GPTAssistant
    assistant = GPTAssistant(project=project, chat_id=chat_id, channel_phone=channel_phone, user_id=user_id)

    # Получение ответа от GPT
    try:
        answer = assistant.ask_question(question)
        return JsonResponse({"anwser": answer})
    except Exception as e:
        return JsonResponse({"error": f"Failed to process the request: {str(e)}"}, status=500)


@csrf_exempt
def validate_google_link(request):
    """
    Проверяет, является ли предоставленная ссылка действительной Google-ссылкой.
    """
    if request.method == "POST":
        link = request.POST.get("link", "").strip()
        if not link:
            return JsonResponse({"valid": False, "message": "Ссылка не указана."})

        # Проверяем, начинается ли ссылка с Google-домена
        if not link.startswith("https://docs.google.com/"):
            return JsonResponse({"valid": False, "message": "Ссылка должна быть Google-документом."})

        # Проверяем доступность ссылки
        try:
            response = requests.head(link, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                return JsonResponse({"valid": True, "message": "Ссылка валидна."})
            else:
                return JsonResponse({"valid": False, "message": "Ссылка недоступна."})
        except requests.RequestException as e:
            return JsonResponse({"valid": False, "message": f"Ошибка проверки: {str(e)}"})

    return JsonResponse({"valid": False, "message": "Некорректный метод запроса."})


@csrf_exempt
def save_google_link(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            google_doc = data.get('google_doc')
            project_id = data.get('project_id')

            if not google_doc or not project_id:
                return JsonResponse({'success': False, 'message': 'Неверные данные'})

            project = Project.objects.get(id=project_id)
            project.google_doc = google_doc
            project.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Только POST-запросы'})


@csrf_exempt
def send_tg_messages(request):

    active_projects = Project.objects.filter(is_active=True)
    for project in active_projects:
        ProjectProcessor.process_project(project)

    return JsonResponse({'success': True})


@csrf_exempt
def get_tg_messages(request):

    active_projects = Project.objects.filter(is_active=True)
    for project in active_projects:
        process_project(project)

    return JsonResponse({'success': True})
