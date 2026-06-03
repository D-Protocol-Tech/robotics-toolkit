"""
============================================================
FILE        : navigation.launch.py
PACKAGE     : robot_bringup
PROJECT     : amr_ros2
DESCRIPTION : Handles navigation stack for all robots.

Launches for each robot:
    1. sensor_interface  — filters LiDAR and odom
    2. slam_module       — real-time mapping
    3. nav2_config       — autonomous navigation

This file is included by bringup.launch.py — not launched
directly.

NAVIGATION MODES:
    mapping    : robot explores and builds the map
    navigation : robot navigates on a saved map
============================================================
"""

import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch.actions import (
    IncludeLaunchDescription,
    TimerAction,
    LogInfo,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource


def load_params(params_file: str) -> dict:
    """Loads params.yaml — returns empty dict if not found."""
    if not os.path.exists(params_file):
        return {}
    with open(params_file, 'r') as f:
        return yaml.safe_load(f)


def generate_navigation_actions(
    params_file: str,
    use_sim_time: str = 'true',
) -> list:
    """
    Builds navigation stack actions for all robots.
    Called by bringup.launch.py — not a standalone launch.

    Returns a list of actions ready to be added to
    a LaunchDescription.
    """
    pkg_sensor = get_package_share_directory('sensor_interface')
    pkg_slam = get_package_share_directory('slam_module')
    pkg_nav2 = get_package_share_directory('nav2_config')

    params = load_params(params_file)
    nav_config = params.get('navigation', {})

    mode = nav_config.get('mode', 'mapping')
    nav_start_delay = float(nav_config.get('nav_start_delay', 15.0))

    actions = []

    actions.append(LogInfo(msg=(
        f'[navigation] Starting navigation stack | mode: {mode}'
    )))

    # ----------------------------------------------------------
    # sensor_interface — starts immediately
    # Filters /scan and /odom before SLAM and Nav2
    # ----------------------------------------------------------
    actions.append(LogInfo(
        msg='[navigation] Step 1/3: sensor_interface starting...'
    ))
    actions.append(IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg_sensor, 'launch', 'sensor_interface.launch.py'
            )
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items()
    ))

    # ----------------------------------------------------------
    # slam_module — starts after 5s
    # Depends on sensor_interface being ready
    # ----------------------------------------------------------
    actions.append(LogInfo(
        msg='[navigation] Step 2/3: slam_module starting (5s delay)...'
    ))
    actions.append(TimerAction(
        period=5.0,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    pkg_slam, 'launch', 'slam_module.launch.py'
                )
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
            }.items()
        )]
    ))

    # ----------------------------------------------------------
    # nav2_config — starts after nav_start_delay
    # Needs SLAM to have built an initial map first
    # ----------------------------------------------------------
    actions.append(LogInfo(msg=(
        f'[navigation] Step 3/3: nav2 starting '
        f'({nav_start_delay}s delay)...'
    )))
    actions.append(TimerAction(
        period=nav_start_delay,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    pkg_nav2, 'launch', 'nav2_config.launch.py'
                )
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
            }.items()
        )]
    ))

    return actions