# core/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

def role_name(user):
    return getattr(getattr(user, 'role', None), 'rolename', None)

class IsClient(BasePermission):
    def has_permission(self, request, view):
        return role_name(request.user) == 'CLIENT'

class IsMaster(BasePermission):
    def has_permission(self, request, view):
        return role_name(request.user) == 'MASTER'

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return role_name(request.user) == 'ADMIN'

class ClientCanCreateOwnOrder(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return role_name(request.user) == 'CLIENT'

class AdminOrMasterCanModify(BasePermission):
    def has_permission(self, request, view):
        rn = role_name(request.user)
        return rn in ('ADMIN', 'MASTER')
