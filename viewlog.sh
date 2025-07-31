#!/bin/sh
touch capsulae2/wsgi.py
echo "RESTARTING...."
sudo tail -f /var/log/apache2/error_capsulae2.log
