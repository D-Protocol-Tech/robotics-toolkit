"""
============================================================
FILE        : slam_module.launch.py
MODULE      : slam_module (kit/)
DESCRIPTION : Launches SLAM mapping stack.

WHAT IT STARTS:
    1. slam_toolbox (async mapping mode)
    2. map_manager node (save/load + statistics)

DEPENDS ON (must be running first):
    - robot_base.launch.py    (provides /tf, /odom)
    - sensor_interface.launch.py (provides /sensors/lidar/filtered)

STANDALONE TEST:
    # Terminal 1
    ros2 launch robot_base robot_base.launch.py
    # Terminal 2
    ros2 launch sensor_interface sensor_interface.launch.py
    # Terminal 3
    ros2 launch slam_module slam_module.launch.py

REUSABILITY:
    Override scan_topic if your robot uses a different
    sensor_interface output topic.
============================================================
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    pkg_slam = get_package_share_directory('slam_module')
    slam_params_file = os.path.join(pkg_slam, 'config', 'default_slam_params.yaml')

    default_maps_dir = os.path.join(pkg_slam, 'maps')
    default_map_path = os.path.join(default_maps_dir, 'house_map')
    default_yaml_file = f"{default_map_path}.yaml"

    if os.path.exists(default_yaml_file):
        default_mode = 'localization'
        slam_map_file = default_map_path
        log_msg = f"[slam_module] Default map found! Automatically selecting LOCALIZATION mode."
    else:
        default_mode = 'mapping'
        slam_map_file = ''
        log_msg = f"[slam_module] No default map found. Automatically selecting MAPPING mode."

    # ----------------------------------------------------------
    # ARGUMENTS
    # ----------------------------------------------------------
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use Gazebo clock'
    )

    map_dir_arg = DeclareLaunchArgument(
        'map_dir',
        default_value=default_maps_dir,
        description='Directory where the map files will be saved'
    )

    map_name_arg = DeclareLaunchArgument(
        'map_name',
        default_value='house_map',
        description='Base name of the saved map files'
    )

    load_map_arg = DeclareLaunchArgument(
        'load_map',
        default_value=default_yaml_file,
        description='The saved map files to load.'
    )

    mode_arg = DeclareLaunchArgument(
        'mode',
        default_value=default_mode,
        description='SLAM mode: mapping or localization'
    )


    # ----------------------------------------------------------
    # NODE 1: slam_toolbox
    # The core SLAM engine — builds map + estimates pose
    # async_slam_toolbox_node = asynchronous mode:
    #   processes scans as fast as possible without blocking
    #   better for simulation (no real-time constraint)
    # ----------------------------------------------------------
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_params_file,
            {
                'use_sim_time':     LaunchConfiguration('use_sim_time'),
                'mode':             LaunchConfiguration('mode'),
                'map_file_name':    slam_map_file,
            }
        ],
    )

    # ----------------------------------------------------------
    # NODE 2: map_manager
    # Saves/loads maps + publishes exploration statistics
    # Delayed 3s to ensure slam_toolbox is ready first
    # ----------------------------------------------------------
    map_manager_node = TimerAction(
        period=3.0,
        actions=[
            Node(
                package='slam_module',
                executable='map_manager',
                name='map_manager',
                output='screen',
                parameters=[
                    slam_params_file,
                    {
                        'use_sim_time': LaunchConfiguration('use_sim_time'),
                        'map_directory': LaunchConfiguration('map_dir'),
                        'map_filename': LaunchConfiguration('map_name'),
                    }
                ],
            )
        ]
    )

    return LaunchDescription([
        use_sim_time_arg,
        map_dir_arg,
        map_name_arg,
        load_map_arg,
        mode_arg,
        slam_toolbox_node,
        map_manager_node,
    ])
