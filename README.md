# AI-система оптимизации энергоэффективности НПЗ

Система для мониторинга, анализа и оптимизации энергопотребления на нефтеперерабатывающем заводе.

**Техлид:** @ripkayato

## Архитектура

Система состоит из 4 сервисов:

1. **data-generator** - генерация синтетических данных
2. **backend** - единый backend сервис с модулями:
   - **ETL** - обработка данных
   - **AI** - прогнозирование и обнаружение аномалий
   - **KPI** - расчёт показателей эффективности
   - **Auth** - аутентификация
3. **database** - PostgreSQL
4. **web-app** - веб-интерфейс

## Структура проекта

```
ai-energy-efficiency/
├── backend/          # Backend сервис (ETL, AI, KPI, Auth)
├── data-generator/   # Генератор данных
├── database/         # SQL скрипты
├── web-app/          # Web приложение
└── docker-compose.yml
```

## Технологии

- **Backend:** FastAPI, Python, SQLAlchemy, Prophet / Node.js, NestJS или Express, Prisma
- **Database:** PostgreSQL
- **Frontend:** Streamlit, Plotly / React, Next.js, Plotly.js
- **Infrastructure:** Docker, Docker Compose

- При желании технологии можно менять (уточняйте)

## Быстрый старт

```bash
# Клонирование репозитория
git clone <repository-url>
cd ai-energy-efficiency

# Запуск системы
docker-compose up --build
```

Доступ:
- Web App: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Git Workflow

Проект использует **Git Flow**:

- `main` - только релизы (защищена)
- `develop` - основная разработка
- `feature/*` - задачи (PR → develop)

### Работа с ветками

```bash
# Создание feature ветки
git checkout develop
git pull origin develop
git checkout -b feature/название-задачи

# После разработки
git push origin feature/название-задачи
# Создать PR в develop
```
