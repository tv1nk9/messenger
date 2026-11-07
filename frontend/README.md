# Фронтенд — React (Vite)

Порт оригинального фронтенда (Jinja-шаблоны + ванильный JS) на React 18.

## Структура

```
frontend/
└── src/
    ├── main.jsx              # точка входа, Bootstrap CSS + стили страниц
    ├── App.jsx               # маршрутизация (/ — чаты, /login — вход) + RequireAuth
    ├── api/client.js         # REST/WS клиент: JWT, refresh-on-401, все эндпоинты бэкенда
    ├── lib/helpers.js        # инициалы, аватар-цвета, форматирование дат, нормализация API-ответов
    ├── hooks/
    │   ├── useMessengerHooks.js  # useDebouncedValue, useChatSocket (WS с автопереподключением)
    │   └── useToast.jsx          # глобальные всплывающие уведомления
    ├── components/           # Avatar, ChatItem, MessageList, UserResultItem, ModalShell (Bootstrap Modal)
    ├── pages/
    │   ├── AuthPage.jsx      # вход + регистрация пользователей админом
    │   └── MessengerPage.jsx # список чатов, поиск, история, realtime WS, группы, приглашения
    ├── auth.css              # перенесённые стили
    └── messenger.css
```

## Разработка

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, прокси /api (включая WS) на FastAPI :8000
```

## Сборка и продакшн

```bash
npm run build      # результат -> ../static/react/
```

`app/main.py` отдаёт собранный SPA на `/` и `/login_page` (читает `static/react/index.html`,
подставляет заголовок страницы). Старые шаблоны в `templates/` больше не используются.
