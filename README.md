# Moskal Auth

Authentication service for Moskal Project built with FastAPI.

## Features
- User registration and authentication
- Email verification
- JWT token based authentication
- Password reset functionality

## Setup
1. Create virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and configure environment variables:
```bash
cp .env.example .env
```

3. Initialize the database:
```bash
python scripts/init_db.py
```

4. Run the application:
```bash
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

## API Documentation
Once the server is running, you can access:
- Interactive API docs (Swagger UI): http://localhost:8000/docs
- Alternative API docs (ReDoc): http://localhost:8000/redoc
