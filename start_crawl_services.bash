#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH=`pwd`
echo "Starting scrapyd..."
ps aux
rm /memex-pinterest/twistd.pid | true
scrapyd --pidfile=/memex-pinterest/twistd.pid &
sleep 15
cd searchengine
scrapyd-deploy scrapyd -p searchengine-project
cd ..
cd crawler
scrapyd-deploy scrapyd -p discovery-project
cd "$(dirname "$0")"
#echo "These are the deployed projects: "
#sleep 5
#scrapyd-deploy -L scrapyd
