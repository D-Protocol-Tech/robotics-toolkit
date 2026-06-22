"""
============================================================
FILE        : nav2_config.launch.py
MODULE      : nav2_config (kit/)
DESCRIPTION : Launches the complete Nav2 navigation stack.

WHAT IT STARTS:
    1. Nav2 bringup (AMCL + planner + controller + BT navigator)
    2. mission_client node (clean goal-sending API)

DEPENDS ON (must be running first):
    - robot_base.launch.py
    - sensor_interface.launch.py
    - slam_module.launch.py   (for /map topic)

STANDALONE TEST:
    # Terminal 1: ros2 launch robot_base robot_base.launch.py
    # Terminal 2: ros2 launch sensor_interface sensor_interface.launch.py
    # Terminal 3: ros2 launch slam_module slam_module.launch.py
    # Terminal 4: ros2 launch nav2_config nav2_config.launch.py

REUSABILITY:
    Override nav2_params_file to use a different config.
    Override map_yaml_file to navigate on a pre-built map.
============================================================
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
)
from launch_ros.actions import Node
from launch.conditions import IfCondition
from launch.substitutions import PythonExpression
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():

    pkg_nav2_config = get_package_share_directory('nav2_config')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    default_mapping_params = os.path.join(
        pkg_nav2_config, 'config', 'default_nav2_mapping_params.yaml'
    )

    default_localization_params = os.path.join(
        pkg_nav2_config, 'config', 'default_nav2_localization_params.yaml'
    )

    # ----------------------------------------------------------
    # ARGUMENTS
    # ----------------------------------------------------------
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use Gazebo clock'
    )
    map_yaml_arg = DeclareLaunchArgument(
        'map_yaml_file', default_value='',
        description='Path to saved map .yaml (empty = use live SLAM map)'
    )
    # Robot namespace for topic remapping
    robot_namespace_arg = DeclareLaunchArgument(
        'robot_namespace',
        default_value='',
        description=(
            'Robot namespace for topic remapping. '
            'Example: robot_001 → /robot_001/cmd_vel. '
            'Empty = no namespace (global topics).'
        )
    )
    mode_arg = DeclareLaunchArgument(
        'mode',
        default_value='mapping',
        description='mapping or localization'
    )
    # NEW — allows passing a custom params file per robot
    # params_file_arg = DeclareLaunchArgument(
    #     'params_file',
    #     default_value=default_mapping_params,
    #     description=(
    #         'Path to nav2 params yaml file. '
    #         'In multi-robot mode, pass a robot-specific '
    #         'params file generated with correct topics.'
    #     )
    # )

    # ----------------------------------------------------------
    # Nav2 bringup
    # Includes all Nav2 nodes: AMCL, planner, controller, BT
    # We use the official nav2_bringup launch as base
    # ----------------------------------------------------------
    nav2_mapping = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg_nav2_bringup, 'launch', 'navigation_launch.py'
            )
        ),
        launch_arguments={
            'use_sim_time':  LaunchConfiguration('use_sim_time'),
            'params_file':   default_mapping_params,
            'autostart':     'true',
            'namespace':     LaunchConfiguration('robot_namespace'),
            'use_namespace': 'true',
        }.items(),
        condition=IfCondition(PythonExpression([
            "'", LaunchConfiguration('mode'), "' == 'mapping'"
        ]))
    )

    # ----------------------------------------------------------
    # Nav2 — localization mode
    # ----------------------------------------------------------
    nav2_localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg_nav2_bringup, 'launch', 'navigation_launch.py'
            )
        ),
        launch_arguments={
            'use_sim_time':  LaunchConfiguration('use_sim_time'),
            'params_file':   default_localization_params,
            'map':           LaunchConfiguration('map_yaml_file'),
            'autostart':     'true',
            'namespace':     LaunchConfiguration('robot_namespace'),
            'use_namespace': 'true',
        }.items(),
        condition=IfCondition(PythonExpression([
            "'", LaunchConfiguration('mode'), "' == 'localization'"
        ]))
    )

    # Relay /cmd_vel → /robot_001/cmd_vel
    # Nav2 publishes on /cmd_vel but robot listens on /robot_001/cmd_vel
    cmd_vel_relay = TimerAction(
        period=3.0,
        actions=[Node(
            package='topic_tools',
            executable='relay',
            name='cmd_vel_relay',
            output='screen',
            arguments=[
                '/cmd_vel',
                ['/', LaunchConfiguration('robot_namespace'), '/cmd_vel']
            ],
            parameters=[{
                'use_sim_time': LaunchConfiguration('use_sim_time'),
            }]
        )]
    )

    # ----------------------------------------------------------
    # mission_client node
    # Clean API for sending navigation goals
    # Delayed 5s to ensure Nav2 is fully started
    # ----------------------------------------------------------
    mission_client_node = TimerAction(
        period=5.0,
        actions=[
            Node(
                package='nav2_config',
                executable='mission_client',
                name='mission_client',
                output='screen',
                parameters=[{
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'robot_name': LaunchConfiguration('robot_namespace'),
                }]
            )
        ]
    )


    return LaunchDescription([
        use_sim_time_arg,
        map_yaml_arg,
        mode_arg,
        robot_namespace_arg,
        # params_file_arg,
        nav2_mapping,
        nav2_localization,
        cmd_vel_relay,
        mission_client_node,
    ])
