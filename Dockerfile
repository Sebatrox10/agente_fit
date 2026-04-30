FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Expondremos este agente en el puerto 8002 para que no choque con el académico
EXPOSE 8002
CMD ["python", "worker_fitness.py"]