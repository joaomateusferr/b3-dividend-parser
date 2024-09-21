#!/bin/bash

if [ $(id -u) -ne 0 ]; then #this screipt equire root privileges (root id is 0)
    echo 'No root privileges detected!'
    echo 'Please, run this script as root'
else
    apt-get -y install python3 python3-pip
    python3 -m pip install openpyxl --break-system-packages
    python3 -m pip install requests --break-system-packages
    python3 -m pip install yfinance --break-system-packages
fi