#!/bin/bash
sudo systemctl stop wegweiser-agent.timer wegweiser-agent.service wegweiser-persistent-agent.service 2>/dev/null
sudo rm -rf /opt/Wegweiser /etc/systemd/system/wegweiser-*
sudo systemctl daemon-reload 2>/dev/null
echo "Done"
