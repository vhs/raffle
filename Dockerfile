FROM ubuntu:latest

ADD draw.sh .

ENTRYPOINT ["./draw.sh"]
