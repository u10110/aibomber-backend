from rest_framework import serializers


from apps.home.models import ClientSettings


class InputStatisticSerializer(serializers.Serializer):
    tg_id = serializers.CharField(max_length=15)
    start_time = serializers.DateTimeField()

    def create(self, validated_data):
        return validated_data


class OutputStatisticSerializer(serializers.Serializer):
    start_time = serializers.DateField()
    end_time = serializers.DateField()
    buyout = serializers.IntegerField()
    likes = serializers.IntegerField()
    feedback_likes = serializers.IntegerField()
    questions = serializers.IntegerField()
    reviews = serializers.IntegerField()

    def create(self, validated_data):
        return validated_data


class SendNotificationsSerializer(serializers.Serializer):
    tg_id = serializers.CharField(max_length=15)
    period_day = serializers.CharField(max_length=50)

    def validate_tg_id(self, value):
        client_settings = ClientSettings.objects.filter(tg_chat_id=value).first()
        if not client_settings:
            raise serializers.ValidationError(f"User settings for {value} not found")
        return client_settings

    def validate_period(self, value):
        status = ["Все", "Раз в день", "Раз в неделю", "Отключить"]
        if value not in status:
            raise serializers.ValidationError(f"Status {value} does not match")
        return value

    def create(self, validated_data):
        return validated_data


class UserAlertsSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(read_only=True)
    tg_id = serializers.SerializerMethodField()
    period_day = serializers.IntegerField()
    send_date = serializers.DateTimeField()

    def get_tg_id(self, obj):
        return obj.clientsettings.tg_chat_id

    def update(self, instance, validated_data):
        instance.send_date = validated_data["send_date"]
        instance.save()
        return instance


class UserDataMessageSerializer(serializers.Serializer):
    tg_chat_id = serializers.CharField(max_length=15)
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    username = serializers.CharField(max_length=50)
    date = serializers.DateTimeField()
    text = serializers.CharField(max_length=100)

    def create(self, validated_data):
        return TgMessage.objects.create(**validated_data)
