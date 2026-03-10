import json

from django.contrib.auth import login, logout
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.crypto import get_random_string
from django.utils.http import urlencode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from apps.authentication.models import User
from apps.home.models import ClientSettings
from apps.telegram.auth.serializers import InputTgUserSerializer


class TgLoginApi(APIView):
    http_method_names = ['get', 'post']
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = InputTgUserSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            phone = serializer.validated_data["phone"]
            user = User.objects.filter(phone=phone).first()
            if not user:
                phone = "+" + phone
                user = User.objects.filter(phone=phone).first()
            client_settings = ClientSettings.objects.filter(
                client=user,
                tg_chat_id=serializer.validated_data["tg_id"]).first()
            if user and client_settings:
                token, _ = Token.objects.get_or_create(user=user)
                login(request, user, backend="apps.authentication.auth_backend.PhoneAuthBackend")
                if user.is_authenticated:
                    return JsonResponse({"token": str(token.key)}, status=status.HTTP_201_CREATED)
            return JsonResponse({"detail": "Invalid credentials provided"}, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TgLogoutApi(APIView):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                request.user.auth_token.delete()
            except (AttributeError, ObjectDoesNotExist):
                pass
            logout(request)
            return JsonResponse({'result': True}, status=status.HTTP_200_OK)
        return JsonResponse({'result': False}, status=status.HTTP_401_UNAUTHORIZED)


@csrf_exempt
@require_POST
def create_magic_link_login(request):
    body = json.loads(request.body.decode('utf-8'))
    phone = body["phone"]
    tg_id = body["tg_id"]
    user = User.objects.filter(phone=phone).first()
    if not user:
        phone = "+" + phone
        user = User.objects.filter(phone=phone).first()
    client_settings = ClientSettings.objects.filter(tg_chat_id=tg_id).first()
    if user and client_settings:
        random_string = get_random_string(16)
        request.session["login_state"] = random_string
        token = signing.dumps({"phone": phone, "login_state": random_string})
        qs = urlencode({"token": token})
        magic_link = request.build_absolute_uri('/') + f"magic_link/?{qs}"
        return JsonResponse({"link": magic_link}, status=status.HTTP_201_CREATED)
    return JsonResponse({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)


@csrf_exempt
@require_GET
def execute_magic_link(request):
    token = request.GET.get("token")
    if not token:
        return HttpResponseRedirect(redirect_to="/", status=status.HTTP_301_MOVED_PERMANENTLY)
    data = signing.loads(token, max_age=60 * 60)
    phone = data["phone"]
    if not phone:
        return HttpResponseRedirect(redirect_to="/", status=status.HTTP_301_MOVED_PERMANENTLY)
    user = User.objects.filter(phone=phone).first()
    if not user:
        phone = phone[0:]
        user = User.objects.filter(phone=phone).first()
        if not user:
            return HttpResponseRedirect(redirect_to="/", status=status.HTTP_301_MOVED_PERMANENTLY)
    # delta = timezone.now() - user.last_login
    # try:
    #     signing.loads(token.replace("%", ":"), max_age=delta)
    # except signing.SignatureExpired:
    #     return HttpResponseRedirect(redirect_to="/", status=status.HTTP_301_MOVED_PERMANENTLY)
    if not request.user.is_authenticated:
        login(request, user, backend="apps.authentication.auth_backend.PhoneAuthBackend")
    if request.user.is_authenticated:
        return HttpResponseRedirect(redirect_to="/delivery?status=all", status=status.HTTP_301_MOVED_PERMANENTLY)
    return HttpResponseRedirect(redirect_to="/",  status=status.HTTP_301_MOVED_PERMANENTLY)
