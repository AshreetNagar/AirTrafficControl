FROM python:3.11

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app/

CMD ["python", "atcTower.py"]
# CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "80"]
# CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "80"]