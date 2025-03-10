from .models import ChatMapping
from datetime import datetime


def get_chat_mapping(integration, chat_id=None, assistant_id=None):
    filters = {"integration": integration}
    if chat_id:
        filters["chat_id"] = chat_id
    if assistant_id:
        filters["assistant_id"] = assistant_id

    return ChatMapping.objects.filter(**filters).first()


def update_chat_mapping(integration, chat_id, assistant_id, thread_id):
    mapping, created = ChatMapping.objects.update_or_create(
        integration=integration,
        chat_id=chat_id,
        defaults={
            "assistant_id": assistant_id,
            "thread_id": thread_id,
            "date_of_creation": datetime.now(),
        },
    )
    return mapping


def delete_chat_mapping(integration, chat_id):
    ChatMapping.objects.filter(integration=integration, chat_id=chat_id).delete()
