"""
============================================================
FILE        : entity.py
PACKAGE     : robot_bringup
PROJECT     : amr_ros2
DESCRIPTION : Handles robot spawning in Gazebo.

Reads params.yaml and spawns N robots at their configured
positions. Each robot gets its own namespace.

This file is included by bringup.launch.py — not launched
directly.

HOW TO ADD A ROBOT:
    1. Open config/params.yaml
    2. Increment num_robots
    3. Add robot_00N section with position config
    4. Relaunch bringup.launch.py
============================================================
"""

import os
import yaml
import copy
from ament_index_python.packages import get_package_share_directory
from launch.actions import (
    IncludeLaunchDescription,
    LogInfo,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare


def load_params(params_file: str) -> dict:
    """
    Loads the project params.yaml file.
    Returns a dict with all configuration values.
    Falls back to empty dict if file not found.
    """
    if not os.path.exists(params_file):
        print(f'[entity] WARNING: params.yaml not found: {params_file}')
        return {}
    with open(params_file, 'r') as f:
        return yaml.safe_load(f)


def get_robot_config(params: dict, robot_key: str) -> dict:
    """
    Returns config for a specific robot.
    Falls back to defaults for any missing value.
    """
    # Get robot-specific config from params.yaml
    robot_params = params.get(robot_key, {})
    defaults = {'name': robot_key}
    # Merge: robot_params overrides defaults
    raw_config = {**defaults, **robot_params}
    return {
        k: v for k, v in raw_config.items()
        if v is not None and str(v).strip() != ''
    }


def make_robot_launch(
    robot_config: dict,
    world_file_path,
    rviz,
) -> IncludeLaunchDescription:
    """
    Builds the launch action for one robot.
    Uses robot_base from kit/ with project-specific config.
    """
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            FindPackageShare('robot_base'),
            '/launch/robot_base.launch.py'
        ]),
        launch_arguments={
            # Robot identity and position
            'robot_name':      str(robot_config.get('name', 'robot_000')),
            'x_pose':          str(robot_config.get('x_pose', 0.0)),
            'y_pose':          str(robot_config.get('y_pose', 0.0)),
            'yaw':             str(robot_config.get('yaw', 0.0)),
            # Safety limits
            'max_linear_vel':  str(robot_config.get('max_linear_vel', 0.5)),
            'max_angular_vel': str(robot_config.get('max_angular_vel', 1.0)),
            # World and visualization
            'world_file':      world_file_path,
            'use_sim_time':    'true',
            'gazebo':          'false',
            # Only first robot opens RViz2
            # (one RViz2 window is enough for the whole fleet)
            'rviz':        rviz,
        }.items()
    )


def generate_entity_actions(
    params_file: str,
    world_file_path,
    rviz,
) -> list:
    """
    Builds the list of spawn actions for all robots.
    Called by bringup.launch.py — not a standalone launch.

    Returns a list of actions ready to be added to
    a LaunchDescription.
    """
    # ----------------------------------------------------------
    # LOAD PROJECT CONFIG
    # ----------------------------------------------------------
    params = load_params(params_file)
    num_robots = params.get('fleet', {}).get('num_robots', 1)

    # ----------------------------------------------------------
    # BUILD ROBOT LAUNCH ACTIONS
    #
    # We read the actual num_robots value from params.yaml
    # (not from LaunchConfiguration — that is a string
    # substitution evaluated later, we need the int now
    # to decide how many robots to spawn).
    # ----------------------------------------------------------
    actions = []

    actions.append(LogInfo(msg=(
        f'[entity] Spawning {num_robots} robot(s) from params.yaml'
    )))

    # Spawn each robot
    for i in range(1, num_robots + 1):
        robot_key = f'robot_{i:03d}'
        robot_config = copy.deepcopy(
            get_robot_config(params, robot_key)
        )
        # Only first robot gets RViz2
        # (avoids opening N RViz2 windows)
        is_first = (i == 1)

        actions.append(LogInfo(msg=(
            f'[entity] Robot {i}: '
            f'name={robot_config.get("name")} '
            f'pos=({robot_config.get("x_pose", 0.0)}, '
            f'{robot_config.get("y_pose", 0.0)})'
        )))

        rviz_arg = rviz if is_first else 'false'

        actions.append(make_robot_launch(
            robot_config=robot_config,
            world_file_path=world_file_path,
            rviz=rviz_arg,
        ))

    return actions