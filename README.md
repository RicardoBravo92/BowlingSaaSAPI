# Bowling SaaS API - Backend

A robust, asynchronous FastAPI backend for a Bowling Alley management system. Built with modern Python tools including SQLModel, SQLAlchemy Async, and Alembic.

## 🚀 Features

- **Authentication**: JWT-based security with Role-Based Access Control (**Owner, Manager, Cashier, Maintenance, User**).
- **Booking System**: Comprehensive reservation logic with availability grids and slot contiguity validation.
- **Email Notifications**: Automated English emails for booking confirmations and password resets (via FastAPI-Mail).
- **Administrative Suite**: Restricted endpoints for managing users, roles, and confirming manual payments.
- **Asynchronous Stack**: Powered by `FastAPI` and `asyncpg` for high performance.
- **Professional Logging**: Structured logging system for better error tracking and audit trails.
- **Database Migrations**: Managed via `Alembic` for safe schema evolution.

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **ORM/ODM**: [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic)
- **Email**: [FastAPI-Mail](https://github.com/sabuhish/fastapi-mail) with Jinja2 templates.
- **Database**: PostgreSQL (via `asyncpg` for app & `psycopg2` for migrations)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Security**: OAuth2 with Password Flow & JWT Tokens

## 📋 Prerequisites

- Python 3.10+
- A PostgreSQL Database (Local or Neon.tech)

## 🔧 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone git@github.com:RicardoBravo92/BowlingSaaSAPI.git
   cd backend
   ```

2. **Install dependencies using uv**:
   Make sure you have [uv](https://github.com/astral-sh/uv) installed, then sync the environment:
   ```bash
   uv sync
   ```

4. **Configure environment variables**:
   Copy the example file and fill in your details:
   ```bash
   cp .env.example .env
   ```
   Or create a `.env` file manually in the root directory. Make sure to set your **SMTP** credentials for the email system to work.

5. **Run Database Migrations**:
   Ensure your database is reachable, then run:
   ```bash
   uv run alembic upgrade head
   ```

6. **Seed Initial Data**:
   Create a default user for each role (Owner, Manager, Cashier, Maintenance, User):
   ```bash
   uv run python seed.py
   ```

## 🚀 Running the Application

Start the development server with hot-reload:

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### 🐳 Running with Docker

This project is fully containerized and optimized to build using `uv`. To run the application alongside an instance of PostgreSQL in Docker:

1. Make sure you have Docker and Docker Compose installed.
2. Ensure your `.env` file is properly configured (the database credentials will be taken from here).
3. Build and run the containers:
   ```bash
   docker-compose up --build
   ```

The application will be exposed on port `8000` and the database on port `5432`.

## 📖 API Documentation

Once the server is running, you can access interactive documentation:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 📂 Project Structure

```text
app/
├── api/             # API routes and dependencies
├── core/            # Config, Security and Database setup
├── models/          # SQLModel database models
├── repositories/    # Data access layer
├── schemas/         # Pydantic/SQLModel validation schemas
├── services/        # Business logic layer
└── templates/       # HTML Email templates
alembic/             # Database migration scripts
tests/               # Pytest suite
```

## 🧪 Testing

Run the test suite to ensure everything is working correctly:
```bash
uv run pytest
```

## 🛡️ License

This project is licensed under the MIT License.
