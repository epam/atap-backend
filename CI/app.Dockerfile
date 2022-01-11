ARG REPO='10.244.220.110/'
FROM ${REPO}node:15.10.0-alpine as axe-install-stage
RUN mkdir /app
WORKDIR /app
RUN npm install axe-core@4.1.3 --save-dev
FROM ${REPO}ubuntu:bionic

ARG APPLICATION_BUILD_REVISION

ENV DEBIAN_FRONTEND noninteractive
ENV DISPLAY :1
ENV PYTHONIOENCODING utf-8
ENV WEB_INTERFACE_STATIC_ROOT=/static/static
ENV WEB_INTERFACE_MEDIA_ROOT=/media/media
ENV USE_DOCKER=True

COPY --from=axe-install-stage /app/node_modules/axe-core/axe.min.js /axe.min.js

RUN apt-get update && apt-get install software-properties-common --yes && add-apt-repository ppa:deadsnakes/ppa --yes && apt-get update && apt-get install python3.7 python3.7-venv python3.7-dev python3-pip firefox ffmpeg firefox-geckodriver tesseract-ocr git git-lfs --yes
RUN git-lfs install
RUN mkdir /app
COPY requirements.txt /app/requirements.txt
RUN python3.7 -m venv /venv
ENV PATH="/venv/bin:$PATH"
ENV NLTK_DATA /models/nltk_data
RUN pip3 install wheel
RUN pip3 install -r /app/requirements.txt
RUN pip3 install --no-binary :all: pyemd==0.5.1 numpy==1.16.4
RUN apt-get update && apt-get install wget
RUN apt-get install -y openjdk-11-jre
ENV APPLICATION_BUILD_REVISION $APPLICATION_BUILD_REVISION
WORKDIR /
RUN wget https://ftp.gnu.org/gnu/freefont/freefont-ttf-20100919.tar.gz
RUN tar xvf freefont-ttf-20100919.tar.gz && rm freefont-ttf-20100919.tar.gz
WORKDIR /app
COPY . .
COPY ./CI/epam.com_rootca.crt /usr/local/share/ca-certificates/
COPY ./CI/epam.com_issuingca.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates
ENV REQUESTS_CA_BUNDLE /etc/ssl/certs/ca-certificates.crt
