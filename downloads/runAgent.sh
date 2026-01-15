#!/bin/bash

while getopts ":m:g:" opt; do
  case ${opt} in
    m )
      MODE=$OPTARG
      ;;
    g )
      GROUPUUID=$OPTARG
      ;;
    \? )
      echo "Invalid option: -$OPTARG" >&2
      usage
      ;;
    : )
      echo "Option -$OPTARG requires an argument." >&2
      usage
      ;;
  esac
done

ROOTDIR="/opt/Wegweiser"
PYTHONAPP="$ROOTDIR/Agent/python-weg/bin/python3"
AGENTCMD="$ROOTDIR/Scripts/agent.py"

if [ -z "$GROUPUUID" ]; then
	echo "commandline: $PYTHONAPP $AGENTCMD" 
	sudo $PYTHONAPP $AGENTCMD 
else
	echo "commandline: $PYTHONAPP $AGENTCMD -g $GROUPUUID" 
	sudo $PYTHONAPP $AGENTCMD -g $GROUPUUID
fi

