# TourMate API

Серверна частина мобільного застосунку туристичного гіда з персоналізованими рекомендаціями.
FastAPI, SQLAlchemy 2, PostgreSQL 16, JWT, bcrypt.

## Запуск

```bash
docker compose up -d db              # PostgreSQL зі схемою та тестовими даними (sql/)
pip install -r requirements.txt
uvicorn app.main:app --reload        # документація API: http://localhost:8000/docs
pytest -v                            # інтеграційні тести API
```

## Архітектура

```text
app/
├── main.py           # застосунок, CORS, журнал запитів
├── config.py         # налаштування зі змінних середовища
├── db.py             # підключення до PostgreSQL
├── models.py         # ORM-моделі за схемою БД
├── schemas.py        # валідація запитів і відповідей
├── security.py       # bcrypt, JWT, ролі
├── errors.py         # єдиний формат помилок {status, message}
├── repositories.py   # доступ до даних
├── services/         # бізнес-логіка: auth, recommendations, walks
└── routers/          # REST API /api/v1
sql/                  # схема, міграція безпеки, тестові дані
tests/                # інтеграційні тести API
```

Тестові облікові записи: tourist@tourmate.ua, author@tourmate.ua, admin@tourmate.ua (пароль secret123).
