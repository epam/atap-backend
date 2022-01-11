ARG REPO='10.244.220.110/'
FROM ${REPO}nginx:1.19.3
COPY nginx_dev_cert /etc/nginx/cert
COPY nginx.conf /etc/nginx/nginx.conf
