FROM python:3.12 

RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY /src/api.py /app/api.py 
COPY /src/worker.py /app/worker.py 
COPY /src/jobs.py /app/jobs.py 

ENTRYPOINT ["python"] 