FROM python:3-alpine 
#o r maybe use slim?

WORKDIR /usr/src/app 
# Python recommends.. Don't like this place.


COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup user && adduser user -G user -S
USER user

COPY . .
CMD [ "python", "./raffle.py"]
