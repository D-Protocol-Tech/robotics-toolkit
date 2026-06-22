"""
============================================================
FILE        : navigation.py
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
import tempfile
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
    
    
def make_robot_nav2_params(
    robot_name: str,
    base_params_file: str,
) -> str:
    """
    Generates a robot-specific Nav2 params file.

    Reads the base params file and replaces all topic
    references with the correct namespaced topics for
    this specific robot.

    Returns the path to the generated temp file.
    """
    with open(base_params_file, 'r') as f:
        params = yaml.safe_load(f)

    # Namespaced topics for this robot
    scan_topic = f'/{robot_name}/sensors/lidar/filtered'
    odom_topic = f'/{robot_name}/odom'

    # Update controller_server odom topic
    cs_params = params.get(
        'controller_server', {}
    ).get('ros__parameters', {})
    cs_params['odom_topic'] = odom_topic

    # Update bt_navigator odom topic
    bt_params = params.get(
        'bt_navigator', {}
    ).get('ros__parameters', {})
    bt_params['odom_topic'] = odom_topic

    # Update velocity_smoother odom topic
    vs_params = params.get(
        'velocity_smoother', {}
    ).get('ros__parameters', {})
    vs_params['odom_topic'] = odom_topic

    # Update scan topics in global_costmap
    gc = params.get('global_costmap', {}).get(
        'global_costmap', {}
    ).get('ros__parameters', {})
    if 'obstacle_layer' in gc:
        if 'scan' in gc['obstacle_layer']:
            gc['obstacle_layer']['scan']['topic'] = scan_topic

    # Update scan topics in local_costmap
    lc = params.get('local_costmap', {}).get(
        'local_costmap', {}
    ).get('ros__parameters', {})
    if 'obstacle_layer' in lc:
        if 'scan' in lc['obstacle_layer']:
            lc['obstacle_layer']['scan']['topic'] = scan_topic

    # Write to a temp file
    tmp = tempfile.NamedTemporaryFile(
        mode='w',
        suffix=f'_{robot_name}_nav2_params.yaml',
        delete=False
    )
    yaml.dump(params, tmp)
    tmp.flush()
    tmp.close()

    return tmp.name



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

    base_nav2_params = os.path.join(
        pkg_nav2, 'config', 'default_nav2_mapping_params.yaml'
    )

    params = load_params(params_file)
    nav_config = params.get('navigation', {})
    chosen_mode = nav_config.get('mode', 'mapping')
    nav_start_delay = float(nav_config.get('nav_start_delay', 25.0))

    # Read robot namespace from params
    fleet_config = params.get('fleet', {})
    num_robots = fleet_config.get('num_robots', 1)

    # Clean and robust maps directory resolution inside share directory
    maps_dir = os.path.join(pkg_bringup, 'maps')

    actions = []

    actions.append(LogInfo(msg=(
        f'[navigation] Starting navigation stack for {num_robots} robot(s)...'
    )))

    for i in range(1, num_robots + 1):
        robot_key = f'robot_{i:03d}'
        robot_config = params.get(robot_key, {})
        robot_name = robot_config.get('name', f'robot_{i:03d}')

        # Namespaced topics unique to this specific robot
        scan_topic = f'/{robot_name}/scan'
        odom_topic = f'/{robot_name}/odom'

        actions.append(LogInfo(
            msg=f'[navigation] Setting up stack for: {robot_name} | '
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
                    'map_dir': maps_dir,
                    'map_name': f'{robot_name}_map',
                    # 'mode': chosen_mode,
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

        # robot_nav2_params = make_robot_nav2_params(
        #     robot_name=robot_name,
        #     base_params_file=base_nav2_params,
        # )

        actions.append(TimerAction(
            period=nav_start_delay,
            actions=[IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_nav2, 'launch', 'nav2_config.launch.py')
                ),
                launch_arguments={
                    'use_sim_time':         use_sim_time,
                    'mode':                 chosen_mode,
                    'robot_namespace':      robot_name,
                    # 'params_file':     robot_nav2_params,
                    # 'map_yaml':   map_file_path,
                }.items()
            )]
        ))

    return actions