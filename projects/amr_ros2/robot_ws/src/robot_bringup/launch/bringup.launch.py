"""
============================================================
FILE        : bringup.launch.py
PACKAGE     : robot_bringup
PROJECT     : amr_ros2
DESCRIPTION : Master launch file — starts the complete AMR project.

WHAT IT DOES:
    1. Launches Gazebo with the project world
    2. Spawns all robots (via entity.launch.py)
    3. Starts navigation stack (via navigation.launch.py)

HOW TO USE:

    # Full system — robots + navigation
    ros2 launch robot_bringup bringup.launch.py

    # Robots only — no navigation (useful for testing spawn)
    ros2 launch robot_bringup bringup.launch.py \
        with_navigation:=false

    # Custom world
    ros2 launch robot_bringup bringup.launch.py \
        world_file:=/path/to/world.world

HOW TO CONFIGURE:
    Edit config/params.yaml to:
    - Change number of robots (fleet.num_robots)
    - Change robot positions and speeds
    - Change navigation mode (mapping/navigation)
============================================================
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import GroupAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

# Import our project helpers
from robot_bringup.entity import generate_entity_actions
from robot_bringup.navigation import generate_navigation_actions


def generate_launch_description():
    """Master launch — orchestrates the complete AMR project."""

    pkg_robot_bringup = get_package_share_directory('robot_bringup')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    params_file = os.path.join(
        pkg_robot_bringup, 'config', 'params.yaml'
    )

    # Resolve world file path
    # Priority: simulation/gazebo/worlds/ > empty world
    candidate_world = os.path.join(
        os.path.dirname(pkg_robot_bringup),
        '..', '..', '..', 'simulation', 'gazebo', 'worlds',
        'amr_world.world'
    )
    candidate_world = os.path.abspath(candidate_world)

    if os.path.exists(candidate_world):
        world_to_load = candidate_world
        world_label = 'amr_world.world'
    else:
        world_to_load = ''
        world_label = 'empty world'

    # ----------------------------------------------------------
    # LAUNCH ARGUMENTS
    # ----------------------------------------------------------
    world_file_arg = DeclareLaunchArgument(
        'world_file',
        default_value=world_to_load,
        description='Path to Gazebo world file.'
    )

    nav2_arg = DeclareLaunchArgument(
        'nav2',
        default_value='true',
        description=(
            'Launch navigation stack (slam + nav2). '
            'Set false to spawn robots only.'
        )
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use Gazebo simulated clock.'
    )

    # ----------------------------------------------------------
    # GAZEBO — launched once for all robots
    # ----------------------------------------------------------
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'world':   world_to_load,
            'verbose': 'false',
        }.items()
    )

    # ----------------------------------------------------------
    # ENTITY ACTIONS — spawn all robots
    # Logic is in robot_bringup/entity.launch.py
    # ----------------------------------------------------------
    entity_actions = generate_entity_actions(
        params_file=params_file,
        world_file_path=world_to_load,
    )

    # ----------------------------------------------------------
    # NAVIGATION ACTIONS — slam + nav2
    # Logic is in robot_bringup/navigation.launch.py
    # ----------------------------------------------------------
    navigation_actions = generate_navigation_actions(
        params_file=params_file,
        use_sim_time='true',
    )

    # ----------------------------------------------------------
    # ASSEMBLE
    # ----------------------------------------------------------
    return LaunchDescription([
        # Arguments
        world_file_arg,
        nav2_arg,
        use_sim_time_arg,
        # Info
        LogInfo(msg=f'[bringup] World: {world_label}'),
        LogInfo(msg='[bringup] Starting AMR project...'),
        # 1. Gazebo
        gazebo,
        # 2. Spawn robots
        *entity_actions,
        # 3. Navigation — only if nav2:=true
        GroupAction(
            condition=IfCondition(
                LaunchConfiguration('nav2')
            ),
            actions=navigation_actions,
        ),
    ])