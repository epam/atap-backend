FROM sameersbn/squid:3.5.27-2
COPY squid.conf /etc/squid/squid.conf
COPY squid_manager.sh /sbin/squid_manager.sh
RUN chmod +x /sbin/squid_manager.sh
RUN mkdir /var/cache/squid && chown proxy:proxy /var/cache/squid
ENTRYPOINT [ "/sbin/squid_manager.sh" ]
