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
    
    def form_invalid(self, form):
        """Called on failed login attempt - single message only"""
        email = form.data.get('username', '')
        
        if email:
            # Check if user is already blocked first
            if redis_blacklist.is_blocked(email):
                ttl = redis_blacklist.get_block_ttl(email)
                minutes = ttl // 60
                seconds = ttl % 60
                
                logger.warning(f"Blocked login attempt: {email}, {ttl} sec remaining")
                messages.error(
                    self.request, 
                    f'Account is temporarily blocked. Try again in {minutes} min {seconds} sec.'
                )
                return super().form_invalid(form)
            
            # Increment failed attempts
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
                    f'Invalid email or password. Attempts remaining: {remaining}'
                )
        
        return super().form_invalid(form)
    
    def form_valid(self, form):
        """Called on successful login"""
        email = form.cleaned_data.get('username', '')
        
        if email:
            redis_blacklist.reset_attempts(email)
            logger.info(f"Successful login: {email}")
        
        return super().form_valid(form)
