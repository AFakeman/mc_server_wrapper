#!/bin/bash

BACKUP_LOCATION="$HOME/Documents/"

function server_log() {
    echo `date '+[%H:%M:%S]'` [Wrapper] "$@"
}

function backup_loop() {
    while : ; do
        cp -r $PWD $BACKUP_LOCATION
        server_log "Backed up the server to $BACKUP_LOCATION"
        sleep 300
    done
}

function cpu_use_loop() {
    while : ; do
        SERVER_PID=`ps aux | grep minecraft_server | tr -s ' ' | cut -f2 -d' ' | head -n1`
        if [ -n "$SERVER_PID" ]; then
            CPU_USE=`top -pid $SERVER_PID -l2 -stats CPU | tail -n1`
            server_log CPU usage: $CPU_USE
        fi
        sleep 30
    done
}

function shutdown() {
    if [ -n $BACKUP_LOOP_PID ]; then
        kill -9 $BACKUP_LOOP_PID
    fi

    if [ -n $CPU_USE_LOOP_PID ]; then
        kill -9 $CPU_USE_LOOP_PID
    fi
}

trap shutdown EXIT

backup_loop &
BACKUP_LOOP_PID=$!
cpu_use_loop &
CPU_USE_LOOP_PID=$!
java -Xms1G -Xmx8G -jar minecraft_server.1.13.2.jar nogui
