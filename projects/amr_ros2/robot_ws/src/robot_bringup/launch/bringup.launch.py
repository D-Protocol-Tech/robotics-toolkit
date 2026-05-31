"""
============================================================
FILE        : bringup.launch.py
PACKAGE     : robot_bringup
PROJECT     : amr_ros2
DESCRIPTION : Master bringup file for the AMR project.

Spawns N robots in Gazebo using the robot_base kit module.
Each robot gets its own configuration from params.yaml.
If a value is missing in params.yaml, the kit default is used.

HOW TO USE:

    # Default — uses params.yaml (num_robots: 1)
    ros2 launch robot_bringup bringup.launch.py

    # Override number of robots at launch time
    ros2 launch robot_bringup bringup.launch.py num_robots:=2
    ros2 launch robot_bringup bringup.launch.py num_robots:=3

    # Custom world
    ros2 launch robot_bringup bringup.launch.py \
        world_file:=/path/to/my_world.world

HOW TO ADD A ROBOT:
    1. Open config/params.yaml
    2. Set num_robots: N
    3. Add a robot_N section with its config
    4. Relaunch — the new robot appears automatically

ARCHITECTURE:
    bringup.launch.py
        reads params.yaml
        └── spawns robot_001 via robot_base.launch.py
        └── spawns robot_002 via robot_base.launch.py (if num_robots >= 2)
        └── spawns robot_003 via robot_base.launch.py (if num_robots >= 3)
        └── ...
============================================================
"""

import os
import yaml
import copy
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare


# ============================================================
# HELPER: load params.yaml
# We read the config file at launch-time (not at runtime)
# so we can use its values to decide how many robots to spawn.
# ============================================================
def load_params(params_file: str) -> dict:
    """
    Loads the project params.yaml file.
    Returns a dict with all configuration values.
    Falls back to empty dict if file not found.
    """
    if not os.path.exists(params_file):
        print(f'[bringup] WARNING: params.yaml not found at {params_file}')
        return {}
    with open(params_file, 'r') as f:
        return yaml.safe_load(f)


# ============================================================
# HELPER: get robot config with defaults
# If a value is missing in params.yaml, use the kit default.
# ============================================================
def get_robot_config(params: dict, robot_key: str) -> dict:
    """
    Returns config for a specific robot (robot_1, robot_2...).
    Falls back to kit defaults for any missing value.
    """

    # Get robot-specific config from params.yaml
    robot_params = params.get(robot_key, {})

    defaults = {
        'name':   robot_key,
    }

    # Merge: robot_params overrides defaults
    raw_config = {**defaults, **robot_params}
    config = {}
    for key, value in raw_config.items():
        if value is not None and str(value).strip() != '':
            config[key] = value

    return config


# ============================================================
# HELPER: build robots launch action
# Creates an IncludeLaunchDescription for robots.
# ============================================================
def make_robot_launch(
    robot_config: dict,
    world_file_path: str,
    use_rviz: str,
) -> IncludeLaunchDescription:
    """
    Builds the launch action for robots.
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
            'max_linear_vel':  str(robot_config.get(
                'max_linear_vel', 0.5
            )),
            'max_angular_vel': str(robot_config.get(
                'max_angular_vel', 1.0
            )),
            # World and visualization
            'world_file':      world_file_path,
            'use_sim_time':    'true',
            'gazebo':          'false',
            # Only first robot opens RViz2
            # (one RViz2 window is enough for the whole fleet)
            'use_rviz':        use_rviz,
        }.items()
    )


def generate_launch_description():
    """
    Main entry point.
    Reads params.yaml and spawns the configured robots.
    """

    # ----------------------------------------------------------
    # PATHS
    # ----------------------------------------------------------
    pkg_robot_bringup = get_package_share_directory('robot_bringup')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    params_file = os.path.join(
        pkg_robot_bringup, 'config', 'params.yaml'
    )

    # Check if project has a custom world file
    # If not → pass empty string → Gazebo loads empty world
    candidate_world = os.path.join(
        pkg_robot_bringup, 'worlds', 'amr_world.world'
    )
    if os.path.exists(candidate_world):
        world_to_load = candidate_world
    else:
        # No world file found → empty world
        world_to_load = ''

    # ----------------------------------------------------------
    # LOAD PROJECT CONFIG
    # ----------------------------------------------------------
    params = load_params(params_file)

    # Read num_robots from params.yaml (default: 1)
    num_robots = params.get('fleet', {}).get('num_robots', 1)

    # ----------------------------------------------------------
    # LAUNCH ARGUMENTS
    # Allow overriding params.yaml values at launch time
    # ----------------------------------------------------------

    world_file_arg = DeclareLaunchArgument(
        'world_file',
        default_value=world_to_load,
        description=(
            'Path to Gazebo world file. '
            'Default: amr_world.world if it exists, '
            'otherwise empty world.'
        )
    )

    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Launch RViz2 for the first robot.'
    )

    # ----------------------------------------------------------
    # BUILD ROBOT LAUNCH ACTIONS
    #
    # We read the actual num_robots value from params.yaml
    # (not from LaunchConfiguration — that is a string
    # substitution evaluated later, we need the int now
    # to decide how many robots to spawn).
    # ----------------------------------------------------------
    actions = []

    gazebo_server_and_client = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'world': world_to_load,
            'verbose': 'false',
        }.items()
    )
    actions.append(gazebo_server_and_client)

    actions.append(LogInfo(msg=(
        f'[AMR bringup] World: '
        f'{"amr_world.world" if world_to_load else "empty world"}'
    )))
    # Log how many robots we are spawning
    actions.append(
        LogInfo(msg=(
            f'[AMR bringup] Spawning {num_robots} robot(s) '
            f'from params.yaml'
        ))
    )

    # Spawn each robot
    for i in range(1, num_robots + 1):
        robot_key = f'robot_{i:03d}'
        robot_config = copy.deepcopy(get_robot_config(params, robot_key))

        # Only first robot gets RViz2
        # (avoids opening N RViz2 windows)
        is_first = (i == 1)

        actions.append(
            LogInfo(msg=(
                f'[AMR bringup] Robot {i}: '
                f'name={robot_config.get("name", f"Unknow_{robot_key}_name")} '
                f'pos=({robot_config["x_pose"]}, '
                f'{robot_config["y_pose"]})'
            ))
        )

        actions.append(
            make_robot_launch(
                robot_config=robot_config,
                world_file_path=world_to_load,
                use_rviz='true' if is_first else 'false',
            )
        )

    # ----------------------------------------------------------
    # ASSEMBLE
    # ----------------------------------------------------------
    return LaunchDescription([
        # Arguments
        world_file_arg,
        use_rviz_arg,
        # Robot launch actions
        *actions,
    ])