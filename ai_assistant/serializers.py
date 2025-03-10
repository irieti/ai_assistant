from rest_framework import serializers
from .models import ChatMapping


class ChatMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMapping
        fields = "__all__"
