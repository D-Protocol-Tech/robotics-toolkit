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
    Builds navigation stack actions for all robots using project-specific configs.
    Called by bringup.launch.py — not a standalone launch.

    Returns a list of actions ready to be added to
    a LaunchDescription.
    """
    pkg_sensor = get_package_share_directory('sensor_interface')
    pkg_slam = get_package_share_directory('slam_module')
    pkg_nav2 = get_package_share_directory('nav2_config')
    pkg_bringup = get_package_share_directory('robot_bringup')

    # Project-specific config files
    slam_params = os.path.join(pkg_bringup, 'config', 'slam_params.yaml')
    nav2_params = os.path.join(pkg_bringup, 'config', 'nav2_params.yaml')

    params = load_params(params_file)
    nav_config = params.get('navigation', {})
    nav_start_delay = float(nav_config.get('nav_start_delay', 25.0))

    # Read robot namespace from params
    # Default: robot_001
    fleet_config = params.get('fleet', {})
    num_robots = fleet_config.get('num_robots', 1)

    # For now navigation is for first robot
    # Multi-robot navigation will be added later
    robot_key = f'robot_{1:03d}'
    robot_config = params.get(robot_key, {})
    robot_name = robot_config.get('name', 'robot_001')

    # Namespaced topics for this robot
    scan_topic = f'/{robot_name}/scan'
    odom_topic = f'/{robot_name}/odom'

    # Maps directory in project
    maps_dir = os.path.join(
        os.path.dirname(pkg_bringup),
        '..', '..', '..', 'src',
        'robot_bringup', 'maps'
    )
    maps_dir = os.path.abspath(maps_dir)
    map_file = os.path.join(maps_dir, 'warehouse_map')

    actions = []

    actions.append(LogInfo(msg=(
        f'[navigation] Starting navigation stack...'
    )))

    actions.append(LogInfo(
        msg=f'[navigation] Robot: {robot_name} | '
            f'scan: {scan_topic} | odom: {odom_topic}'
    ))

    # ----------------------------------------------------------
    # sensor_interface — starts immediately
    # Filters /scan and /odom before SLAM and Nav2
    # ----------------------------------------------------------
    actions.append(LogInfo(
        msg='[navigation] Step 1/3: sensor_interface...'
    ))
    actions.append(IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_sensor, 'launch', 'sensor_interface.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            # Override default /scan with robot namespaced topic
            'input_topic':  scan_topic,
            'odom_input_topic': odom_topic,
        }.items()
    ))

    # ----------------------------------------------------------
    # slam_module — starts after 5s
    # Depends on sensor_interface being ready
    # ----------------------------------------------------------
    actions.append(LogInfo(
        msg='[navigation] Step 2/3: slam_module (5s delay)...'
    ))
    actions.append(TimerAction(
        period=5.0,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_slam, 'launch', 'slam_module.launch.py')
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
                # Pass our project slam config
                'params_file':  slam_params,
            }.items()
        )]
    ))

    # ----------------------------------------------------------
    # nav2_config — starts after nav_start_delay
    # Needs SLAM to have built an initial map first
    # nav2 — delayed to give SLAM time to build initial map
    # ----------------------------------------------------------
    actions.append(LogInfo(msg=(
        f'[navigation] Step 3/3: nav2 ({nav_start_delay}s delay)...'
    )))
    actions.append(TimerAction(
        period=nav_start_delay,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_nav2, 'launch', 'nav2_config.launch.py')
            ),
            launch_arguments={
                'use_sim_time':         use_sim_time,
                # Pass our project nav2 config
                'params_file':          nav2_params,
                'robot_namespace':      robot_name,
            }.items()
        )]
    ))

    return actions