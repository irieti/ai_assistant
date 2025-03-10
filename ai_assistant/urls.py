from django.urls import path
from .views import ChatMappingListView, ChatMappingDetailView

urlpatterns = [
    path("chats/", ChatMappingListView.as_view(), name="chat-list"),
    path(
        "chats/<str:integration>/<str:chat_id>/",
        ChatMappingDetailView.as_view(),
        name="chat-detail",
    ),
    path("chats/", ChatMappingListView.as_view(), name="chat-list"),
    path(
        "chats/<str:integration>/<str:chat_id>/",
        ChatMappingDetailView.as_view(),
        name="chat-detail",
    ),
]
