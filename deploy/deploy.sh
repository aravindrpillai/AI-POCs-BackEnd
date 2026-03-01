#!/bin/bash
cd /root/AI-POCs-BackEnd

git pull origin main

source /root/venv/bin/activate
pip install -r requirements.txt

python manage.py migrate

systemctl restart gunicorn

echo "Deployed successfully"