FROM python:3.10

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

# Railway menyediakan env var $PORT secara dinamis saat runtime, jadi perlu
# bentuk shell (bukan exec form) agar variabelnya ikut di-expand.
# migrate dan collectstatic dijalankan setiap start supaya skema database &
# static files selalu sinkron dengan kode yang baru dideploy.
CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn project.wsgi --bind 0.0.0.0:${PORT:-8000}