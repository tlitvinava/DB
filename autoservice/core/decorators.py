from django.shortcuts import redirect
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role is None or request.user.role.rolename != "admin":
            return redirect('home')  # или страница ошибки
        return view_func(request, *args, **kwargs)
    return wrapper
