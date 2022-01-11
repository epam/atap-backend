#!/bin/bash
/sbin/entrypoint.sh &
entry_pid=$!
while :
do
  if [ -f /squid_control/restart ]; then
    echo Stopping Squid...
    pkill squid
    sleep 5
    echo Killing Squid...
    pkill -9 squid
    sleep 5
    echo Removing cache directories...
    rm -rf /var/cache/squid/*
    echo Starting Squid...
    /sbin/entrypoint.sh &
    sleep 10
    echo Removing message file...
    rm /squid_control/restart
    echo Cache Restarted
  fi
  sleep 1
done
