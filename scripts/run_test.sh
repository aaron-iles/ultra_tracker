#!/usr/bin/env bash

for line in $(cat $2); do 
    curl -X POST http://0.0.0.0:8080/ping \
        -d ${line} \
        -H 'Content-Type: application/json; charset=UTF-8' \
        -H "x-outbound-auth-token: $1"
    read -p "Press Enter to continue..."
done
