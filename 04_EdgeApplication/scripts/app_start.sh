#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

if [ "$SM_EDGE_AGENT_HOME" == "" ]; then
    echo "You need to define the env var: SM_EDGE_AGENT_HOME"
    exit
fi

echo "SM_EDGE_AGENT_HOME: $SM_EDGE_AGENT_HOME"
AGENT_PID_FILE='/tmp/edge_agent.pid'
APP_PID_FILE='/tmp/edge_app.pid'
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

mkdir -p $SM_EDGE_AGENT_HOME/logs
if ! test -f "$AGENT_PID_FILE" || ! kill -0 $(cat $AGENT_PID_FILE) 2> /dev/null; then
    echo "Starting the agent"
    cd $SM_EDGE_AGENT_HOME/bin
    rm -f nohup.out /tmp/edge_agent
    nohup ./sagemaker_edge_agent_binary -a /tmp/edge_agent -c ../sagemaker_edge_config.json >> $SM_EDGE_AGENT_HOME/logs/agent.log 2>&1 &
    AGENT_PID=$!
    echo $AGENT_PID > $AGENT_PID_FILE
fi
echo "AGENT PID: $(cat $AGENT_PID_FILE)"

 
if ! test -f "$APP_PID_FILE" || ! kill -0 $(cat $APP_PID_FILE) 2> /dev/null; then
    sleep 5
    echo "Starting the app"
    cd $DIR/..
    rm -f nohup.out
    nohup ./run.py >> $SM_EDGE_AGENT_HOME/logs/app.log 2>&1 &
    APP_PID=$!
    echo $APP_PID > $APP_PID_FILE
fi
echo "APP PID: $(cat $APP_PID_FILE)"

