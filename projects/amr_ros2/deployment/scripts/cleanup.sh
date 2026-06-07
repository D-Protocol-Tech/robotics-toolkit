#!/bin/bash
# ============================================================
# cleanup.sh — Use only when Gazebo crashes or freezes.
# Normal Ctrl+C does not require this script.
# ============================================================
echo "Cleaning up Gazebo and ROS 2 residuals..."
sudo pkill -9 -f gzserver 2>/dev/null
sudo pkill -9 -f gzclient 2>/dev/null
sudo pkill -9 -f gazebo    2>/dev/null
rm -rf /tmp/ros_*
sleep 2
echo "Done. You can relaunch now."
