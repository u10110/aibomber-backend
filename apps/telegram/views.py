from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.alert.models import TgMessage
from apps.telegram.models import PeriodicAlerts
from apps.telegram.permissions import StatisticPermission, KeywordPermission
from apps.telegram.serializers import InputStatisticSerializer, OutputStatisticSerializer, \
    SendNotificationsSerializer, UserAlertsSerializer, UserDataMessageSerializer


class GetStatisticView(APIView):
    http_method_names = ['post']
    permission_classes = [StatisticPermission]

    def post(self, request, *args, **kwargs):
        serializer = InputStatisticSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
            return JsonResponse(serializer.errors, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SendNotificationsView(APIView):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        serializer = SendNotificationsSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            user_settings = serializer.validated_data["tg_id"]
            period = serializer.validated_data["period_day"]
            alert = PeriodicAlerts.objects.filter(clientsettings=user_settings)
            if alert.count() > 1:
                alert.delete()
            else:
                if alert:
                    first = alert.first()
                    first.period_day = period
                    first.save()
                    return JsonResponse({"detail": "Task updated successfully"}, status=status.HTTP_201_CREATED)
                else:
                    alert = PeriodicAlerts.objects.create(clientsettings=user_settings, period_day=period)
                    if not alert:
                        return JsonResponse({"detail": "Task was not added"}, status=status.HTTP_404_NOT_FOUND)
                    return JsonResponse({"detail": "Task added successfully"}, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAlertsView(viewsets.ModelViewSet):
    queryset = PeriodicAlerts.objects.all()
    permission_classes = [StatisticPermission]
    serializer_class = UserAlertsSerializer


class SaveTgMessagesView(APIView):
    http_method_names = ['post']
    permission_classes = [KeywordPermission]

    def post(self, request, *args, **kwargs):
        serializer = UserDataMessageSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
