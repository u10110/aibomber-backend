# -*- encoding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt


from apps.home import views
from apps.home import api

urlpatterns = [

    
    path('messages/', views.chat_messages, name='messages'),
    path('api/chats/<int:chat_id>/toggle_auto_active/', views.toggle_auto_active, name='toggle_auto_active'),
    path('api/chats/<int:chat_id>/change_status/', views.change_status, name='change_status'),



    path("get-tochka-phone/", views.get_tochka_phone, name="get-tochka-phone"),

    
    path('templates/<str:page_name>/', views.dynamic_page),

    path('channels/send-code/', views.send_code, name='send_code'),
    path('channels/verify-code/', views.verify_code, name='verify_code'),
    path('channels/create-app/', views.create_app, name='create_app'),

    

    path('create-project-chat/', views.create_project_chat, name='create_project_chat'),
    path('validate-google-link/', views.validate_google_link, name='validate_google_link'),



    path("api/chats/", login_required(api.chats), name="chats-list"),
    path("api/chats/export", login_required(api.chats_export), name="chats-list"),
    path('api/chat/<int:chat_id>/', login_required(api.chat_messages), name='chat-messages'),
    path('api/chat/<int:chat_id>/message/', login_required(api.send_chat_messages), name='send-chat-messages'),
    path('api/chat/<int:chat_id>/photo/', login_required(api.chat_photo), name='chat-photo'),
    path('api/send-to-gpt/', csrf_exempt(api.send_to_gpt), name='send-to-gpt'),
    path('api/telethon-sessions/', login_required(api.telethon_sessions), name='telethon-sessions'),
    path('api/delete-telethon-session/', login_required(api.delete_telethon_session), name='delete-telethon-sessions'),

    path('api/v1/gpt-assistant/', views.gpt_assistant, name='gpt_assistant'),

    path("api/channels/", login_required(api.channels), name="api-channels"),
    path('api/channel/', login_required(api.channel_create), name='api-channel-create'),
    path('api/channel/<int:channel_id>/', login_required(api.channel_get), name='api-channel-get'),
    path('api/channel/<int:channel_id>/update/', login_required(api.channel_update), name='api-channel-update'),
    path('api/channel/<int:channel_id>/delete', login_required(api.channel_delete), name='api-channel-delete'),
    path('api/channel/send-code/', login_required(views.send_code), name='api-channel-send-code'),
    path('api/channel/is-auth/', login_required(views.is_auth), name='api-channel-is-auth'),
    path('api/channel/verify-code/', login_required(api.verify_code), name='api-channel-verify-code'),
    path('api/channel/send-password/', login_required(api.send_password), name='api-channel-send-password'),

    path("api/projects/", login_required(api.projects), name="api_projects"),
    path('api/projects/toggle-active/', views.toggle_project_active, name='api-toggle-project-active'),
    path('api/project/', login_required(api.project_create), name='api-project-create'),
    path('api/project/<int:project_id>/', login_required(api.project_get_or_save), name='api-project-save'),
    path('api/project/<int:project_id>/delete', login_required(api.project_delete), name='api-project-delete'),

    path("api/recipients/", login_required(api.recipients), name="api-recipient"),
    path('api/recipient/', login_required(api.recipient_create), name='api-recipient-create'),
    path('api/recipient/<int:recipient_id>/', login_required(api.recipient_get_or_save), name='api-recipient-save'),
    path('api/recipient/<int:recipient_id>/delete', login_required(api.recipient_delete), name='api-recipient-delete'),


    path('api/file-upload', login_required(api.file_upload), name='file-upload'),

    path("api/balance", login_required(api.get_balance), name="balance"),


]

