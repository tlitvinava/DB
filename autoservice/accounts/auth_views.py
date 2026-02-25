# -*- coding: utf-8 -*-
from django.contrib.auth import views as auth_views
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from core.redis_blacklist import redis_blacklist
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class LoginViewWithBlacklist(auth_views.LoginView):
    """Custom LoginView with Redis blacklist check"""
    
    template_name = 'registration/login.html'
    
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            email = request.POST.get('username', '')
            
            if email:
                if redis_blacklist.is_blocked(email):
                    ttl = redis_blacklist.get_block_ttl(email)
                    minutes = ttl // 60
                    seconds = ttl % 60
                    
                    logger.warning(f"Blocked login attempt: {email}, {ttl} sec remaining")
                    messages.error(
                        request, 
                        f'Account is temporarily blocked. Try again in {minutes} min {seconds} sec.'
                    )
                    return self.render_to_response(self.get_context_data())
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_invalid(self, form):
        """Called on failed login attempt"""
        email = form.data.get('username', '')
        
        if email:
            attempts = redis_blacklist.increment_attempts(email)
            remaining = settings.MAX_LOGIN_ATTEMPTS - attempts
            
            logger.warning(f"Failed login attempt: {email}, attempt {attempts}/{settings.MAX_LOGIN_ATTEMPTS}")
            
            if attempts >= settings.MAX_LOGIN_ATTEMPTS:
                redis_blacklist.block_user(email)
                logger.error(f"User blocked: {email} after {attempts} attempts")
                messages.error(
                    self.request,
                    f'Account blocked for 10 minutes after {settings.MAX_LOGIN_ATTEMPTS} failed attempts.'
                )
            else:
                messages.warning(
                    self.request,
                    f'Invalid email or password. Attempts remaining: {attempts}'
                )
        
        return super().form_invalid(form)
    
    def form_valid(self, form):
        """Called on successful login"""
        email = form.cleaned_data.get('username', '')
        
        if email:
            redis_blacklist.reset_attempts(email)
            logger.info(f"Successful login: {email}")
        
        return super().form_valid(form)
