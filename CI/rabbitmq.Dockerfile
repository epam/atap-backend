ARG REPO='10.244.220.110/'
FROM ${REPO}rabbitmq:3.8.9
COPY rabbitmq-isolated.conf /etc/rabbitmq/rabbitmq.conf
