FROM python:3.9
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app/
RUN apt-get update && apt-get install curl nano iputils-ping libpq-dev awscli -y
ADD usermanagementservice/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY usermanagementservice/ /app
COPY common/ /app/app/common
ENV PYTHONPATH=/app
EXPOSE 80
RUN chmod -R 777 /app/app/common
RUN chmod +x /app/app/common/entrypoint.sh
ENTRYPOINT ["/app/app/common/entrypoint.sh"]
# ENTRYPOINT ["tail", "-f", "/dev/null"]