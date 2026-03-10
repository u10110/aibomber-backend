from rest_framework import permissions


class StatisticPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        auth_type = request.headers.get('Authorization')
        if auth_type == "Rundeck":
            return True
        return bool(request.user and request.user.is_authenticated)


class KeywordPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        auth_type = request.headers.get('Authorization')
        if auth_type == "Direct":
            return True
        return bool(request.user and request.user.is_authenticated)
