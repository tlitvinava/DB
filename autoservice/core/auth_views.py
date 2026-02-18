from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .redis_blacklist import redis_blacklist
from django.conf import settings

User = get_user_model()


class JWTLoginView(APIView):
    """JWT Login с защитой от брутфорса через Redis блэклист"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'error': 'Email и пароль обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, заблокирован ли пользователь
        if redis_blacklist.is_blocked(email):
            ttl = redis_blacklist.get_block_ttl(email)
            minutes = ttl // 60
            seconds = ttl % 60
            return Response(
                {
                    'error': 'Пользователь временно заблокирован',
                    'message': f'Попробуйте снова через {minutes} мин {seconds} сек',
                    'blocked': True,
                    'ttl_seconds': ttl
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Увеличиваем счетчик попыток даже если пользователь не существует
            # (чтобы не давать информацию о существовании email)
            attempts = redis_blacklist.increment_attempts(email)
            self._check_and_block(email, attempts)
            return Response(
                {'error': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Проверяем пароль
        if not user.check_password(password):
            attempts = redis_blacklist.increment_attempts(email)
            remaining_attempts = settings.MAX_LOGIN_ATTEMPTS - attempts
            
            self._check_and_block(email, attempts)
            
            return Response(
                {
                    'error': 'Неверный email или пароль',
                    'remaining_attempts': max(0, remaining_attempts)
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Успешная авторизация - сбрасываем попытки
        redis_blacklist.reset_attempts(email)
        
        # Генерируем JWT токены
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Авторизация успешна',
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'surname': user.surname,
                'role_id': user.role_id if hasattr(user, 'role_id') else None,
            }
        }, status=status.HTTP_200_OK)
    
    def _check_and_block(self, email, attempts):
        """Проверяет нужно ли заблокировать пользователя"""
        if attempts >= settings.MAX_LOGIN_ATTEMPTS:
            redis_blacklist.block_user(email)


class JWTLogoutView(APIView):
    """Logout с добавлением токена в блэклист"""
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {'message': 'Выход выполнен успешно'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CheckBlockStatusView(APIView):
    """Проверка статуса блокировки пользователя"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        email = request.query_params.get('email')
        if not email:
            return Response(
                {'error': 'Email обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_blocked = redis_blacklist.is_blocked(email)
        ttl = redis_blacklist.get_block_ttl(email) if is_blocked else 0
        attempts = redis_blacklist.get_attempts(email)
        
        return Response({
            'email': email,
            'is_blocked': is_blocked,
            'remaining_time_seconds': ttl,
            'remaining_time_formatted': f"{ttl // 60} мин {ttl % 60} сек" if ttl > 0 else None,
            'failed_attempts': attempts,
            'max_attempts': settings.MAX_LOGIN_ATTEMPTS
        })


class UnblockUserView(APIView):
    """Разблокировка пользователя (только для администраторов)"""
    
    def post(self, request):
        # Проверяем, что пользователь - администратор
        if not request.user.is_staff and getattr(request.user, 'role_id', None) != 1:
            return Response(
                {'error': 'Доступ запрещен. Требуются права администратора.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        email = request.data.get('email')
        if not email:
            return Response(
                {'error': 'Email обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        redis_blacklist.unblock_user(email)
        
        return Response({
            'message': f'Пользователь {email} разблокирован'
        })
