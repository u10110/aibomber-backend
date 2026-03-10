from rest_framework import serializers


class InputTgUserSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    tg_id = serializers.CharField(max_length=10)

    def create(self, validated_data):
        return validated_data
