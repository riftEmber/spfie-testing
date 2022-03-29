FROM riftember/spf-ie:latest

RUN git rev-parse --short HEAD

RUN apt update && \
    apt install -y python3

COPY . .

RUN python3 --version

#COPY requirements.txt ./
#RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /spf-ie/resources

CMD [ "python3", "./process-sources.py" ]
