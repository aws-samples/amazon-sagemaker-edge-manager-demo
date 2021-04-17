#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

AGENT_PID_FILE='/tmp/edge_agent.pid'
APP_PID_FILE='/tmp/edge_app.pid'

if test -f "$AGENT_PID_FILE" && kill -0 $(cat $AGENT_PID_FILE) 2> /dev/null; then
    echo "Stopping the agent"
    kill $(cat $AGENT_PID_FILE)
    rm -f $AGENT_PID_FILE
fi
 
if test -f "$APP_PID_FILE" && kill -0 $(cat $APP_PID_FILE) 2> /dev/null; then
    echo "Stopping the app"
    kill $(cat $APP_PID_FILE)
    rm -f $APP_PID_FILE
fi
