FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard.py .
COPY analyze_dashboard.py .

EXPOSE 8050

CMD ["python", "-u", "dashboard.py"]
