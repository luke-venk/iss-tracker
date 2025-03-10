FROM python:3.12

RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/
RUN pip3 install -r /app/requirements.txt
COPY iss_app.py /app/
COPY test_iss_app.py /app/

RUN chmod +rx /app/iss_app.py
ENV PATH="/app:$PATH"

CMD ["./iss_app.py"]