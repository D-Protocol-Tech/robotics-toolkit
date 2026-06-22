"""
============================================================
FILE        : robot_base.launch.py
MODULE      : robot_base (kit/)
DESCRIPTION : Flexible robot base launcher.

WHAT IT STARTS:
    1. Gazebo simulator (empty world or custom world)
    2. robot_state_publisher (broadcasts URDF + TF tree)
    3. Spawns the robot model in Gazebo
    4. base_controller node (safety + status)

ARGUMENTS:
    robot_name      : unique robot ID (default: robot_000)
    x_pose          : spawn X position in meters (default: 0.0)
    y_pose          : spawn Y position in meters (default: 0.0)
    yaw             : spawn orientation in radians (default: 0.0)
    urdf_path       : path to custom URDF/Xacro (default: built-in ROBOT)
    world_file      : path to custom .world file (default: empty world)
    use_sim_time    : use Gazebo clock (default: true)
    use_rviz        : auto-launch RViz2 (default: false)
    max_linear_vel  : safety speed limit m/s (default: 0.5)
    max_angular_vel : safety rotation limit rad/s (default: 1.0)

USAGE EXAMPLES:

    # Default robot, default world
    ros2 launch robot_base robot_base.launch.py gazebo:=true

    # Your own robot URDF
    ros2 launch robot_base robot_base.launch.py gazebo:=true \
        urdf_path:=/path/to/my_robot.urdf

    # Custom world
    ros2 launch robot_base robot_base.launch.py gazebo:=true \
        world_file:=/path/to/robot_world.world \
        x_pose:=2.0 y_pose:=1.0

    # With RViz2 auto-launched
    ros2 launch robot_base robot_base.launch.py gazebo:=true rviz:=true

    # Slower safer robot
    ros2 launch robot_base robot_base.launch.py gazebo:=true \
        max_linear_vel:=0.2 max_angular_vel:=0.3

    # Two robots at different positions (run in two terminals)
    ros2 launch robot_base robot_base.launch.py gazebo:=true \
        robot_name:=robot_001 x_pose:=0.0 y_pose:=0.5
    ros2 launch robot_base robot_base.launch.py gazebo:=true \
        robot_name:=robot_002 x_pose:=0.0 y_pose:=-0.5

STANDALONE:
    ros2 launch robot_base robot_base.launch.py gazebo:=true

INCLUDED FROM PARENT LAUNCH FILE:
    IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            FindPackageShare('robot_base'),
            '/launch/robot_base.launch.py'
        ]),
        launch_arguments={
            'robot_name':  'robot_001',
            'urdf_path':   '/path/to/my_robot.urdf',
            'world_file':  '/path/to/robot_world.world',
            'x_pose':      '0.0',
            'y_pose':      '0.5',
        }.items()
    )
============================================================
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    Command,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Generate the complete launch description for robot_base."""

    # ----------------------------------------------------------
    # PACKAGE PATHS
    # ----------------------------------------------------------
    pkg_robot_base = get_package_share_directory('robot_base')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

    # Default files (built-in robot)
    default_urdf = os.path.join(
        pkg_robot_base, 'urdf', 'default_robot.urdf.xacro'
    )
    default_params = os.path.join(
        pkg_robot_base, 'config', 'default_params.yaml'
    )

    # ----------------------------------------------------------
    # LAUNCH ARGUMENTS
    # Each argument has:
    #   - a name
    #   - a default value (used if not overridden)
    #   - a description (shown with --show-args)
    # ----------------------------------------------------------

    # Robot identity
    robot_name_arg = DeclareLaunchArgument(
        'robot_name',
        default_value='robot_000',
        description=(
            'Unique robot identifier. '
            'Use different names for multi-robot setups: '
            'robot_001, robot_002, my_robot...'
        )
    )

    # Spawn position — where the robot appears in Gazebo
    x_pose_arg = DeclareLaunchArgument(
        'x_pose',
        default_value='0.0',
        description=(
            'Robot starting X position in Gazebo world (meters). '
            'For multi-robot: give each robot a different position '
            'so they do not overlap. Example: 0.0, 1.0, -1.0...'
        )
    )
    y_pose_arg = DeclareLaunchArgument(
        'y_pose',
        default_value='0.0',
        description=(
            'Robot starting Y position in Gazebo world (meters). '
            'Example: robot_001 y_pose:=0.5, robot_002 y_pose:=-0.5'
        )
    )
    yaw_arg = DeclareLaunchArgument(
        'yaw',
        default_value='0.0',
        description=(
            'Robot starting orientation in radians. '
            '0.0   = facing +X axis (East). '
            '1.57  = facing +Y axis (North). '
            '3.14  = facing -X axis (West). '
            '-1.57 = facing -Y axis (South).'
        )
    )

    # Robot description — use built-in or your own
    urdf_path_arg = DeclareLaunchArgument(
        'urdf_path',
        default_value=default_urdf,
        description=(
            'Path to robot URDF or Xacro file. '
            'Default: built-in robot (default_robot.urdf.xacro). '
            'Override to use your own robot design: '
            'urdf_path:=/path/to/my_robot.urdf'
        )
    )

    # World file — use empty world or your own
    world_file_arg = DeclareLaunchArgument(
        'world_file',
        default_value='',
        description=(
            'Path to Gazebo .world file. '
            'Default: empty world (no obstacles). '
            'Override to use your own environment: '
            'world_file:=/path/to/robot_world.world'
        )
    )

    # Simulation clock
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description=(
            'Use Gazebo simulated clock (true) or wall clock (false). '
            'Always true for simulation. '
            'Set to false only when running on a real physical robot.'
        )
    )

    # RViz2 & Gazebo auto-launch
    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='false',
        description=(
            'Automatically launch RViz2 for visualization (true/false). '
            'Default false to save resources. '
            'Set true when you want to see the robot immediately.'
        )
    )
    gazebo_arg = DeclareLaunchArgument(
        'gazebo',
        default_value='false',
        description=(
            'Automatically launch Gazebo for visualization in the world (true/false). '
            'Default false when not in standalone mode. '
            'Set true when in standalone mode.'
        )
    )

    # Velocity safety limits
    max_linear_vel_arg = DeclareLaunchArgument(
        'max_linear_vel',
        default_value='0.5',
        description=(
            'Maximum forward/backward speed in m/s. '
            'The robot will never exceed this speed regardless '
            'of what Nav2 or teleop commands. '
            'Reduce for tight spaces or fragile environments.'
        )
    )
    max_angular_vel_arg = DeclareLaunchArgument(
        'max_angular_vel',
        default_value='1.0',
        description=(
            'Maximum rotation speed in rad/s. '
            'Reduce if robot tips over during sharp turns.'
        )
    )


    # ----------------------------------------------------------
    # NODE 1: robot_state_publisher
    #
    # This node reads the URDF and continuously broadcasts
    # the position of every robot part (TF transforms).
    # Every other module (SLAM, Nav2, RViz) needs this.
    #
    # ParameterValue with value_type=str is REQUIRED in
    # ROS 2 Humble when passing xacro output as parameter.
    # Without it ROS 2 tries to parse URDF as YAML → crash.
    # ----------------------------------------------------------
    robot_description = ParameterValue(
        Command([
            'xacro ',
            LaunchConfiguration('urdf_path'),
            ' robot_name:=',
            LaunchConfiguration('robot_name')
        ]),
        value_type=str
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        namespace=LaunchConfiguration('robot_name'),
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }]
    )

    # ----------------------------------------------------------
    # ACTION: Launch Gazebo
    #
    # We include Gazebo's own launch file.
    # world argument: empty string = empty world.
    # ----------------------------------------------------------
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg_gazebo_ros, 'launch', 'gazebo.launch.py'
            )
        ),
        launch_arguments={
            'world':   LaunchConfiguration('world_file'),
            'verbose': 'false',
        }.items(),
        condition=IfCondition(LaunchConfiguration('gazebo'))
    )

    # ----------------------------------------------------------
    # NODE 2: spawn_entity
    #
    # Sends the URDF to Gazebo to physically create the robot.
    # Delayed 3 seconds to ensure Gazebo is fully loaded.
    # Uses all pose arguments for flexible positioning.
    # ----------------------------------------------------------
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_robot',
        output='screen',
        arguments=[
            # Topic namespaced per robot:
            # robot_001 → /robot_001/robot_description
            '-topic',
            ['/', LaunchConfiguration('robot_name'),
             '/robot_description'],
            '-entity', LaunchConfiguration('robot_name'),
            '-x',     LaunchConfiguration('x_pose'),
            '-y',     LaunchConfiguration('y_pose'),
            '-Y',     LaunchConfiguration('yaw'),
            '-z',     '0.1',
        ],
    )

    # ----------------------------------------------------------
    # NODE 3: base_controller
    #
    # Safety layer: clamps velocities to max limits.
    # Status publisher: JSON on /robot_status.
    # Delayed 5s to start after robot is spawned.
    # Velocity limits come from launch arguments so the
    # user can set them without editing any file.
    # ----------------------------------------------------------
    base_controller_node = Node(
        package='robot_base',
        executable='base_controller',
        namespace=LaunchConfiguration('robot_name'),
        name='base_controller',
        output='screen',
        parameters=[
            default_params,
            {
                'use_sim_time': LaunchConfiguration(
                    'use_sim_time'
                ),
                'robot_name': LaunchConfiguration(
                    'robot_name'
                ),
                'max_linear_velocity': LaunchConfiguration(
                    'max_linear_vel'
                ),
                'max_angular_velocity': LaunchConfiguration(
                    'max_angular_vel'
                ),
            }
        ]
    )

    # ----------------------------------------------------------
    # NODE 4: RViz2 (optional)
    #
    # Only launched if rviz:=true.
    # IfCondition checks the launch argument value.
    # ----------------------------------------------------------
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    # ----------------------------------------------------------
    # ASSEMBLE LAUNCH DESCRIPTION
    # Order: arguments first, then nodes in startup order.
    # ----------------------------------------------------------
    return LaunchDescription([
        # 1. Declare all arguments
        gazebo_arg,
        robot_name_arg,
        x_pose_arg,
        y_pose_arg,
        yaw_arg,
        urdf_path_arg,
        world_file_arg,
        use_sim_time_arg,
        rviz_arg,
        max_linear_vel_arg,
        max_angular_vel_arg,
        # 2. Start nodes
        robot_state_publisher_node,
        gazebo,
        spawn_robot,
        base_controller_node,
        rviz_node,
    ])
