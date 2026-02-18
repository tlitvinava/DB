from django.contrib.auth import views as auth_views
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from .redis_blacklist import redis_blacklist
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class LoginViewWithBlacklist(auth_views.LoginView):
    """Кастомный LoginView с проверкой Redis блэклиста"""
    
    template_name = 'registration/login.html'
    
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        # Проверяем блокировку до обработки формы
        if request.method == 'POST':
            email = request.POST.get('username', '')  # Django использует username для email
            
            if email:
                # Проверяем, заблокирован ли пользователь
                if redis_blacklist.is_blocked(email):
                    ttl = redis_blacklist.get_block_ttl(email)
                    minutes = ttl // 60
                    seconds = ttl % 60
                    
                    logger.warning(f"Заблокированная попытка входа: {email}, осталось {ttl} сек")
                    messages.error(
                        request, 
                        f'Пользователь временно заблокирован. Попробуйте через {minutes} мин {seconds} сек.'
                    )
                    return self.render_to_response(self.get_context_data())
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_invalid(self, form):
        """Вызывается при неудачной попытке входа"""
        email = form.data.get('username', '')
        
        if email:
            # Увеличиваем счетчик попыток
            attempts = redis_blacklist.increment_attempts(email)
            remaining = settings.MAX_LOGIN_ATTEMPTS - attempts
            
            logger.warning(f"Неудачная попытка входа: {email}, попытка {attempts}/{settings.MAX_LOGIN_ATTEMPTS}")
            
            # Проверяем, нужно ли заблокировать
            if attempts >= settings.MAX_LOGIN_ATTEMPTS:
                redis_blacklist.block_user(email)
                logger.error(f"Пользователь заблокирован: {email} после {attempts} попыток")
                messages.error(
                    self.request,
                    f'Пользователь заблокирован на 10 минут после {settings.MAX_LOGIN_ATTEMPTS} неудачных попыток.'
                )
            else:
                # Показываем сколько осталось попыток
                messages.warning(
                    self.request,
                    f'Неверный email или пароль. Осталось попыток: {remaining}'
                )
        
        return super().form_invalid(form)
    
    def form_valid(self, form):
        """Вызывается при успешном входе"""
        email = form.cleaned_data.get('username', '')
        
        if email:
            # Сбрасываем счетчик попыток
            redis_blacklist.reset_attempts(email)
            logger.info(f"Успешный вход: {email}")
        
        return super().form_valid(form)
