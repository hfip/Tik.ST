FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
# استخدمنا shell form هنا ليتمكن من قراءة متغير البيئة $PORT
CMD uvicorn api.index:app --host 0.0.0.0 --port ${PORT:-10000}
