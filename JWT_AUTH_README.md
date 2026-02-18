# JWT Авторизация с Redis Блэклистом

## Обзор проекта

Это Django REST API для автосервиса с JWT-аутентификацией и защитой от брутфорса через Redis.

## Оценка текущего проекта

### Плюсы:
- Хорошая структура с разделением на приложения (core, accounts)
- Кастомная модель пользователя с email в качестве username
- Использование DRF для API
- Наличие ролей (admin, master, client)
- CRUD операции с логированием

### Минусы:
- Использовалась только сессионная аутентификация (не подходит для API)
- Отсутствовала защита от брутфорса
- Не было rate limiting
- Некоторые дублирующиеся функции в views.py

### Что добавлено:
1. **JWT Authentication** через `djangorestframework-simplejwt`
2. **Redis блэклист** для блокировки после 3 неудачных попыток
3. **API endpoints** для логина/логаута с проверкой блокировки
4. **Docker Compose** для Redis

## Установка и запуск

### 1. Установка зависимостей

```bash
cd autoservice
pip install -r ../requirements.txt
```

### 2. Запуск Redis через Docker

```bash
cd ..  # в корень проекта
docker-compose up -d
```

Проверка работы Redis:
```bash
docker exec -it autoservice_redis redis-cli ping
# Должен вернуть: PONG
```

### 3. Применение миграций

```bash
cd autoservice
python manage.py migrate
```

### 4. Запуск сервера

```bash
python manage.py runserver
```

## API Endpoints

### JWT Аутентификация

#### 1. Логин с защитой от брутфорса
```
POST /api/auth/login/
```

**Тело запроса:**
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

**Успешный ответ (200):**
```json
{
    "success": true,
    "message": "Авторизация успешна",
    "tokens": {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    },
    "user": {
        "id": 1,
        "email": "user@example.com",
        "name": "Иван",
        "surname": "Иванов",
        "role_id": 3
    }
}
```

**Ошибка авторизации (401):**
```json
{
    "error": "Неверный email или пароль",
    "remaining_attempts": 2
}
```

**Пользователь заблокирован (403):**
```json
{
    "error": "Пользователь временно заблокирован",
    "message": "Попробуйте снова через 10 мин 0 сек",
    "blocked": true,
    "ttl_seconds": 600
}
```

#### 2. Логаут
```
POST /api/auth/logout/
```

**Заголовки:**
```
Authorization: Bearer <access_token>
```

**Тело запроса:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### 3. Проверка статуса блокировки
```
GET /api/auth/check-block/?email=user@example.com
```

**Ответ:**
```json
{
    "email": "user@example.com",
    "is_blocked": true,
    "remaining_time_seconds": 540,
    "remaining_time_formatted": "9 мин 0 сек",
    "failed_attempts": 0,
    "max_attempts": 3
}
```

#### 4. Разблокировка пользователя (только админ)
```
POST /api/auth/unblock/
```

**Заголовки:**
```
Authorization: Bearer <admin_access_token>
```

**Тело запроса:**
```json
{
    "email": "user@example.com"
}
```

### Стандартные JWT Endpoints (DRF SimpleJWT)

#### Получение токена
```
POST /api/token/
```

**Тело запроса:**
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

#### Обновление access токена
```
POST /api/token/refresh/
```

**Тело запроса:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

## Как протестировать

### Тест 1: Успешная авторизация

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "correctpassword"
  }'
```

**Ожидаемый результат:** Получение JWT токенов

### Тест 2: Неудачная авторизация (счетчик попыток)

```bash
# Попытка 1
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "wrongpassword"
  }'

# Ответ: "remaining_attempts": 2

# Попытка 2
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "wrongpassword"
  }'

# Ответ: "remaining_attempts": 1
```

### Тест 3: Блокировка после 3 неудачных попыток

```bash
# Попытка 3 (последняя)
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "wrongpassword"
  }'

# Попытка 4 (пользователь уже заблокирован)
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "correctpassword"
  }'

# Ответ: 403 Forbidden
# {
#   "error": "Пользователь временно заблокирован",
#   "message": "Попробуйте снова через 10 мин 0 сек"
# }
```

### Тест 4: Проверка статуса блокировки

```bash
curl "http://localhost:8000/api/auth/check-block/?email=test@example.com"
```

**Ожидаемый результат:**
```json
{
    "email": "test@example.com",
    "is_blocked": true,
    "remaining_time_seconds": 600,
    "remaining_time_formatted": "10 мин 0 сек",
    "failed_attempts": 0,
    "max_attempts": 3
}
```

### Тест 5: Разблокировка администратором

```bash
# 1. Логинимся как админ
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "adminpassword"
  }'

# 2. Разблокируем пользователя
curl -X POST http://localhost:8000/api/auth/unblock/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{
    "email": "test@example.com"
  }'

# Ответ: {"message": "Пользователь test@example.com разблокирован"}
```

### Тест 6: Доступ к защищенным API с JWT

```bash
# Получаем токен
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "correctpassword"
  }'

# Используем access_token для доступа к API
curl http://localhost:8000/api/orders/ \
  -H "Authorization: Bearer <access_token>"
```

### Тест 7: Проверка логаут (blacklist токена)

```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "refresh": "<refresh_token>"
  }'

# После этого refresh_token нельзя использовать для обновления access
```

## Настройки

### Redis настройки (settings.py)
```python
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Настройки блокировки
MAX_LOGIN_ATTEMPTS = 3
LOGIN_BLOCK_DURATION = 600  # 10 минут в секундах
```

### JWT настройки (settings.py)
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

## Безопасность

1. **Защита от брутфорса**: После 3 неудачных попыток пользователь блокируется на 10 минут
2. **Сокрытие информации**: При неверном email или пароле выдается одинаковое сообщение
3. **JWT токены**: Короткое время жизни access токена (30 минут)
4. **Redis**: Хранение данных о попытках в памяти с TTL
5. **Админ может разблокировать**: Возможность ручной разблокировки

## Известные ограничения

1. Блэклист работает только для JWT авторизации (не влияет на стандартную сессионную)
2. Redis должен быть запущен отдельно (через Docker или локально)
3. При перезапуске Redis данные о попытках сбрасываются (если нет persist)

## Дополнительные команды Redis

```bash
# Проверить все ключи в Redis
docker exec -it autoservice_redis redis-cli keys "*"

# Посмотреть значение конкретного ключа
docker exec -it autoservice_redis redis-cli get "blocked:user@example.com"
docker exec -it autoservice_redis redis-cli get "login_attempts:user@example.com"

# Удалить ключ
docker exec -it autoservice_redis redis-cli del "blocked:user@example.com"

# Очистить все данные (осторожно!)
docker exec -it autoservice_redis redis-cli flushall
```
