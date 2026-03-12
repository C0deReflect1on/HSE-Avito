# Техническое задание: Реализация JWT-авторизации

## 1. Общие сведения

### 1.1. Цель

Реализовать систему аутентификации и авторизации пользователей на основе JWT-токенов в существующем backend-сервисе. После реализации все эндпоинты предсказаний и модерации должны быть защищены проверкой авторизации.

### 1.2. Итоговое поведение системы

- Сервис умеет авторизовывать пользователя по логину и паролю через эндпоинт `/login`
- При успешной авторизации клиенту устанавливается `HttpOnly`-cookie с JWT-токеном
- Все эндпоинты предсказаний и модерации проверяют наличие и валидность токена
- Заблокированные аккаунты не могут авторизоваться
- Пароли хранятся в БД в хэшированном виде
- Все тесты промаркированы и запускаются автономно (нужен только Docker с PostgreSQL)

### 1.3. Новые зависимости

Добавить в `requirements.txt`:

```
pyjwt>=2.8.0
```

---

## 2. Инфраструктура

### 2.1. Docker Compose

Убедиться, что в `docker-compose.yaml` присутствует PostgreSQL с **фиксированными** параметрами:

```yaml
postgres:
  image: postgres:16
  environment:
    POSTGRES_DB: hw
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
  ports:
    - "5435:5432"
  volumes:
    - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Подключение к БД — порт `5435`, credentials — `postgres:postgres`, база — `hw`.

---

## 3. Задачи

---

### 3.1. Миграция — таблица `account`

**Файл:** `db/migrations/V004__account.sql`

```sql
CREATE TABLE IF NOT EXISTS account (
    id SERIAL PRIMARY KEY,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE
);
```

- `login` — уникален
- `password` — хранится в хэшированном виде (см. п. 3.6)
- `is_blocked` — флаг блокировки, по умолчанию `FALSE`

---

### 3.2. Модели данных

Добавить Pydantic-схемы (в `app/schemas.py` или отдельный файл):

```python
class Account(BaseModel):
    id: int
    login: str
    is_blocked: bool

class LoginRequest(BaseModel):
    login: str
    password: str
```

> Поле `password` **не включается** в модель `Account`, чтобы хэш не утекал в ответы или логи.

---

### 3.3. Исключения

Добавить в `app/exceptions.py`:

```python
class AuthenticationError(Exception):
    """Неверные учётные данные"""

class AccountBlockedError(Exception):
    """Аккаунт заблокирован"""

class InvalidTokenError(Exception):
    """Невалидный или истёкший токен"""
```

---

### 3.4. Репозиторий аккаунтов

**Файл:** `app/repositories/account_repository.py`

Класс `AccountRepository`. Методы:

| Метод | Сигнатура | Описание |
|---|---|---|
| `create` | `(login: str, hashed_password: str) → Account` | Создать аккаунт |
| `get_by_id` | `(account_id: int) → Account \| None` | Поиск по ID |
| `get_by_login` | `(login: str) → Account \| None` | Поиск по логину |
| `get_by_credentials` | `(login: str, hashed_password: str) → Account \| None` | Поиск по логину + хэшу пароля |
| `block` | `(account_id: int) → bool` | Установить `is_blocked = TRUE` |
| `delete` | `(account_id: int) → bool` | Удалить аккаунт |

Экспортировать из `app/repositories/__init__.py`.

> Таблица `account` заполняется только из тестов через репозиторий (имитация синхронизации с внешней системой). Отдельного эндпоинта регистрации не требуется.

#### Тесты

**Файл:** `tests/test_account_repository.py`
**Маркер:** `@pytest.mark.integration`

| Тест-кейс | Что проверяет |
|---|---|
| `test_create_account` | Создание, возврат корректных полей |
| `test_create_duplicate_login` | Дубль логина → ошибка |
| `test_get_by_id_found` | Существующий аккаунт по ID |
| `test_get_by_id_not_found` | Несуществующий → `None` |
| `test_get_by_login` | Поиск по логину |
| `test_get_by_credentials_valid` | Верные credentials → аккаунт |
| `test_get_by_credentials_invalid` | Неверный пароль → `None` |
| `test_block_account` | Блокировка → `is_blocked == True` |
| `test_delete_account` | Удаление → повторный поиск → `None` |

---

### 3.5. Сервис авторизации

**Файл:** `app/services/auth_service.py`

Класс `AuthService`. Принимает `AccountRepository` через конструктор.

#### Конфигурация JWT

Добавить в `app/config.py`:

```python
JWT_SECRET_KEY: str = "your-secret-key"  # переопределяется через env
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRATION_SECONDS: int = 3600  # 1 час
```

#### Методы

| Метод | Описание |
|---|---|
| `authenticate(login, password) → Account` | Хэширует пароль → ищет через `get_by_credentials` → проверяет `is_blocked` → возвращает `Account`. При ошибке бросает `AuthenticationError` или `AccountBlockedError` |
| `create_token(account) → str` | Генерирует JWT. Payload: `{"user_id": account.id, "login": account.login, "exp": <timestamp>}` |
| `verify_token(token) → dict` | Декодирует JWT, возвращает payload. При невалидном/истёкшем токене бросает `InvalidTokenError` |

#### Тесты

**Файл:** `tests/test_auth_service_unit.py`
**Маркер:** `@pytest.mark.unit`

Репозиторий замокан.

| Тест-кейс | Что проверяет |
|---|---|
| `test_authenticate_success` | Корректные credentials → `Account` |
| `test_authenticate_invalid_credentials` | Неверные credentials → `AuthenticationError` |
| `test_authenticate_blocked_account` | Заблокированный аккаунт → `AccountBlockedError` |
| `test_create_token_contains_user_id` | Payload содержит `user_id` |
| `test_create_token_contains_exp` | Payload содержит корректное время истечения |
| `test_verify_token_valid` | Валидный токен → payload |
| `test_verify_token_expired` | Истёкший токен → `InvalidTokenError` |
| `test_verify_token_invalid_signature` | Подписан другим секретом → `InvalidTokenError` |
| `test_verify_token_malformed` | Мусорная строка → `InvalidTokenError` |

---

### 3.6. Хэширование паролей

**Файл:** `app/services/password_hasher.py`

```python
import hashlib

def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()
```

**Где применяется:**

1. **`AccountRepository.create`** — перед записью в БД пароль хэшируется (или хэш передаётся снаружи)
2. **`AuthService.authenticate`** — перед вызовом `get_by_credentials` пароль хэшируется
3. В тестах при создании аккаунтов — пароль также пропускается через `hash_password`

> Минимально достаточно `md5`. При желании можно использовать `bcrypt` или `sha256`.

---

### 3.7. Эндпоинт `/login`

**Файл:** `app/routers/auth.py`

#### Спецификация

```
POST /login
Content-Type: application/json

Request Body:
{
    "login": "string",
    "password": "string"
}

Response 200:
  Set-Cookie: access_token=<jwt_token>; HttpOnly; Path=/
  Body: {"message": "Authorized", "user_id": <int>}

Response 401:
  Body: {"detail": "Invalid credentials"}

Response 403:
  Body: {"detail": "Account is blocked"}
```

#### Логика

1. Принять `LoginRequest` (login, password)
2. Вызвать `auth_service.authenticate(login, password)`
3. Вызвать `auth_service.create_token(account)`
4. Установить cookie: `response.set_cookie(key="access_token", value=token, httponly=True)`
5. Вернуть ответ с `user_id`

Зарегистрировать роутер в `app/main.py`:

```python
from app.routers.auth import router as auth_router
app.include_router(auth_router)
```

#### Тесты

**Файл:** `tests/test_auth_router.py`
**Маркер:** `@pytest.mark.unit` и/или `@pytest.mark.integration`

| Тест-кейс | Что проверяет |
|---|---|
| `test_login_success` | POST /login → 200, cookie `access_token` установлена |
| `test_login_invalid_credentials` | Неверный пароль → 401 |
| `test_login_blocked_account` | Заблокированный аккаунт → 403 |
| `test_login_missing_fields` | Без обязательных полей → 422 |
| `test_login_cookie_is_httponly` | Cookie помечена `HttpOnly` |

---

### 3.8. Dependency для проверки авторизации

**Файл:** `app/dependencies.py` (дополнить)

#### Реализация

```python
async def get_current_account(request: Request) -> Account:
    """
    1. Извлечь токен из cookie 'access_token'
    2. Вызвать auth_service.verify_token(token)
    3. По user_id из payload получить аккаунт через repository.get_by_id
    4. Проверить, что аккаунт существует и не заблокирован
    5. Вернуть объект Account
    На любом шаге ошибка → HTTPException(status_code=401)
    """
```

**Ключевое требование:** dependency возвращает полную модель `Account`, а **не** просто `user_id`.

#### Подключение

Добавить `Depends(get_current_account)` во **все** handlers:

- `app/routers/predict.py` — все эндпоинты
- `app/routers/moderation_result.py` — все эндпоинты

Пример:

```python
@router.post("/predict")
async def predict(
    request: PredictRequest,
    account: Account = Depends(get_current_account),
):
    ...
```

> **Исключение:** эндпоинт `POST /login` **НЕ** защищается.

#### Тесты

**Файл:** `tests/test_auth_dependency_unit.py`
**Маркер:** `@pytest.mark.unit`

| Тест-кейс | Что проверяет |
|---|---|
| `test_valid_token_returns_account` | Корректный токен → `Account` |
| `test_missing_cookie` | Нет cookie → 401 |
| `test_invalid_token` | Невалидный токен → 401 |
| `test_expired_token` | Истёкший токен → 401 |
| `test_blocked_account` | Аккаунт заблокирован → 401 |
| `test_account_not_found` | Аккаунт удалён → 401 |
| `test_predict_without_auth` | `POST /predict` без cookie → 401 |
| `test_predict_with_auth` | `POST /predict` с валидной cookie → 200 |

---

## 4. Итоговая структура новых/изменённых файлов

```
db/migrations/
  V004__account.sql                          # NEW

app/
  config.py                                  # CHANGED — JWT-настройки
  dependencies.py                            # CHANGED — get_current_account
  exceptions.py                              # CHANGED — новые исключения
  schemas.py                                 # CHANGED — Account, LoginRequest
  main.py                                    # CHANGED — регистрация auth роутера
  repositories/
    account_repository.py                    # NEW
    __init__.py                              # CHANGED — экспорт
  routers/
    auth.py                                  # NEW
    predict.py                               # CHANGED — добавлен Depends
    moderation_result.py                     # CHANGED — добавлен Depends
  services/
    auth_service.py                          # NEW
    password_hasher.py                       # NEW

tests/
  test_account_repository.py                 # NEW — integration
  test_auth_service_unit.py                  # NEW — unit
  test_auth_router.py                        # NEW — unit/integration
  test_auth_dependency_unit.py               # NEW — unit

requirements.txt                             # CHANGED — pyjwt
```

---

## 5. Требования к тестам

1. **Маркировка:** все тесты помечены `@pytest.mark.unit` или `@pytest.mark.integration`
2. **Автономность:** тесты запускаются без внешних зависимостей, кроме Docker с PostgreSQL (порт `5435`)
3. **Изоляция:** unit-тесты используют моки для зависимостей (репозиторий, сервисы)
4. **Запуск:**
   - Все тесты: `pytest`
   - Только unit: `pytest -m unit`
   - Только интеграционные: `pytest -m integration`

---

## 6. Критерии приёмки

- [ ] Миграция `V004__account.sql` применяется без ошибок
- [ ] Репозиторий аккаунтов реализован, интеграционные тесты проход