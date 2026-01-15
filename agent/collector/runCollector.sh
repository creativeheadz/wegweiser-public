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


if [ -z "$MODE" ]; then
	MODE="AUDIT"
	echo "MODE: $MODE"
else 
	echo "MODE: $MODE"
fi

if [ -z "$GROUPUUID" ]; then
	echo "commandline: /opt/Wegweiser/venv/bin/python3 /opt/Wegweiser/Collector/collector.py -m $MODE" 
	sudo /opt/Wegweiser/venv/bin/python3 /opt/Wegweiser/Collector/collector.py -m $MODE 
else
	echo "commandline: /opt/Wegweiser/venv/bin/python3 /opt/Wegweiser/Collector/collector.py -m $MODE -g $GROUPUUID" 
	sudo /opt/Wegweiser/venv/bin/python3 /opt/Wegweiser/Collector/collector.py -m $MODE -g $GROUPUUID
fi

