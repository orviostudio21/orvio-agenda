FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_DEBUG=0
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home app
COPY --chown=app:app . .
RUN DJANGO_DEBUG=0 DJANGO_SECRET_KEY=collectstatic-build-only-placeholder python manage.py collectstatic --noinput
USER app
EXPOSE 8000
CMD ["waitress-serve", "--listen=0.0.0.0:8000", "config.wsgi:application"]
