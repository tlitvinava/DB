import redis
from django.conf import settings

# Попытка подключиться к Redis, если не получится - используем in-memory
class RedisBlacklist:
    """Класс для работы с Redis блэклистом для блокировки пользователей"""
    
    def __init__(self):
        self._memory_storage = {}  # In-memory fallback
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2  # Короткий таймаут
            )
            # Проверяем подключение
            self.redis_client.ping()
            self.use_redis = True
            print("✅ Redis подключен успешно")
        except (redis.ConnectionError, redis.ResponseError) as e:
            self.use_redis = False
            print(f"⚠️  Redis недоступен ({e}). Используется in-memory хранилище (данные будут потеряны при перезапуске)")
    
    def get_attempts_key(self, email):
        """Ключ для хранения количества попыток входа"""
        return f"login_attempts:{email}"
    
    def get_block_key(self, email):
        """Ключ для хранения статуса блокировки"""
        return f"blocked:{email}"
    
    def increment_attempts(self, email):
        """Увеличивает счетчик неудачных попыток входа"""
        key = self.get_attempts_key(email)
        if self.use_redis:
            attempts = self.redis_client.incr(key)
            self.redis_client.expire(key, settings.LOGIN_BLOCK_DURATION)
            return attempts
        else:
            # In-memory реализация
            import time
            current_time = time.time()
            if key not in self._memory_storage:
                self._memory_storage[key] = {'count': 0, 'expires': current_time + settings.LOGIN_BLOCK_DURATION}
            self._memory_storage[key]['count'] += 1
            return self._memory_storage[key]['count']
    
    def get_attempts(self, email):
        """Возвращает количество неудачных попыток входа"""
        key = self.get_attempts_key(email)
        if self.use_redis:
            attempts = self.redis_client.get(key)
            return int(attempts) if attempts else 0
        else:
            import time
            current_time = time.time()
            if key in self._memory_storage:
                if self._memory_storage[key]['expires'] > current_time:
                    return self._memory_storage[key]['count']
                else:
                    del self._memory_storage[key]
            return 0
    
    def block_user(self, email):
        """Блокирует пользователя на указанное время"""
        key = self.get_block_key(email)
        if self.use_redis:
            self.redis_client.setex(key, settings.LOGIN_BLOCK_DURATION, "blocked")
            self.redis_client.delete(self.get_attempts_key(email))
        else:
            import time
            self._memory_storage[key] = {'blocked': True, 'expires': time.time() + settings.LOGIN_BLOCK_DURATION}
            # Удаляем попытки
            attempts_key = self.get_attempts_key(email)
            if attempts_key in self._memory_storage:
                del self._memory_storage[attempts_key]
    
    def is_blocked(self, email):
        """Проверяет, заблокирован ли пользователь"""
        key = self.get_block_key(email)
        if self.use_redis:
            return self.redis_client.exists(key) > 0
        else:
            import time
            if key in self._memory_storage:
                if self._memory_storage[key]['expires'] > time.time():
                    return True
                else:
                    del self._memory_storage[key]
            return False
    
    def get_block_ttl(self, email):
        """Возвращает оставшееся время блокировки в секундах"""
        key = self.get_block_key(email)
        if self.use_redis:
            ttl = self.redis_client.ttl(key)
            return ttl if ttl > 0 else 0
        else:
            import time
            if key in self._memory_storage:
                remaining = int(self._memory_storage[key]['expires'] - time.time())
                return max(0, remaining)
            return 0
    
    def reset_attempts(self, email):
        """Сбрасывает счетчик попыток (при успешном входе)"""
        key = self.get_attempts_key(email)
        if self.use_redis:
            self.redis_client.delete(key)
        else:
            if key in self._memory_storage:
                del self._memory_storage[key]
    
    def unblock_user(self, email):
        """Разблокирует пользователя вручную"""
        if self.use_redis:
            self.redis_client.delete(self.get_block_key(email))
            self.redis_client.delete(self.get_attempts_key(email))
        else:
            block_key = self.get_block_key(email)
            attempts_key = self.get_attempts_key(email)
            if block_key in self._memory_storage:
                del self._memory_storage[block_key]
            if attempts_key in self._memory_storage:
                del self._memory_storage[attempts_key]

# Singleton instance
redis_blacklist = RedisBlacklist()
