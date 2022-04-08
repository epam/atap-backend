ARG REPO='10.244.220.110/'
FROM ${REPO}debian:buster
RUN apt-get update && apt-get install xserver-xorg-video-dummy procps --yes
COPY xorg.conf /etc/X11/xorg.conf
HEALTHCHECK CMD ps -e | grep X
CMD ["/usr/bin/Xorg", "-noreset", "+extension", "GLX", "+extension", "RANDR", "+extension", "RENDER", "-logfile", "./xdummy.log", "-config", "/etc/X11/xorg.conf", ":1"]
