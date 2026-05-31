# Module : `robot_base`

**kit/** — Reusable across any ROS 2 differential-drive robot project.

---

## What this module does

`robot_base` is the **physical foundation** of any robot project.
It handles everything related to the robot's body and its
presence in the simulation.

Concretely it :
- Describes the robot physically via URDF/Xacro
  (chassis, wheels, LiDAR, camera)
- Launches the Gazebo simulator and spawns the robot inside
- Broadcasts TF transforms so every other module knows
  where each robot part is in space
- Simulates a 360° LiDAR sensor with realistic noise
- Enforces velocity safety limits (robot never exceeds them,
  regardless of what Nav2 or teleop sends)
- Publishes robot status as JSON on `/robot_status`

---

## Prerequisites

This module requires the following ROS 2 packages to be installed:

```bash
sudo apt install -y \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-robot-state-publisher \
    ros-humble-xacro \
    ros-humble-rviz2
```

---

## ROS 2 Interface

### Topics

| Direction | Topic | Type | Description |
|-----------|-------|------|-------------|
| IN | `/cmd_vel` | `geometry_msgs/Twist` | Velocity command |
| OUT | `/odom` | `nav_msgs/Odometry` | Wheel odometry |
| OUT | `/scan` | `sensor_msgs/LaserScan` | 360° LiDAR data |
| OUT | `/robot_description` | `std_msgs/String` | URDF string |
| OUT | `/robot_status` | `std_msgs/String` | JSON status |
| OUT | `/tf` | `tf2_msgs/TFMessage` | Transform tree |
| OUT | `/tf_static` | `tf2_msgs/TFMessage` | Static transforms |

### Robot status format (`/robot_status`)

Published every second as a JSON string :

```json
{
  "robot_name":   "robot_001",
  "linear_vel":   0.234,
  "angular_vel":  0.012,
  "position_x":   1.452,
  "position_y":  -0.231,
  "total_cmds":   147
}
```

---

## Launch arguments

All arguments have sensible defaults.
**Override only what you need.**

| Argument | Default | Description |
|----------|---------|-------------|
| `robot_name` | `robot_000` | Unique robot identifier. Use different names for multi-robot setups. |
| `x_pose` | `0.0` m | Robot spawn X position in Gazebo world. |
| `y_pose` | `0.0` m | Robot spawn Y position in Gazebo world. |
| `yaw` | `0.0` rad | Robot spawn orientation. See orientation table below. |
| `urdf_path` | built-in robot | Path to a custom URDF or Xacro file. |
| `world_file` | empty world | Path to a custom Gazebo `.world` file. |
| `use_sim_time` | `true` | Use Gazebo clock. Set `false` for a real physical robot. |
| `use_rviz` | `false` | Auto-launch RViz2 for visualization. |
| `max_linear_vel` | `0.5` m/s | Safety speed limit. Robot never exceeds this. |
| `max_angular_vel` | `1.0` rad/s | Safety rotation limit. |
| `gazebo` | `false` | Only open gazebo in standalone mode |

### Orientation reference (`yaw` argument)

            +Y (North)
                 |
                 |
        -X ------+------ +X (East)   ← yaw = 0.0 (default)
                 |
                 |
            -Y (South)

- yaw =  0.00  → robot faces East  (+X)
- yaw =  1.57  → robot faces North (+Y)
- yaw =  3.14  → robot faces West  (-X)
- yaw = -1.57  → robot faces South (-Y)

---

## Usage examples

### See all available arguments
```bash
ros2 launch robot_base robot_base.launch.py --show-args
```

### Default — built-in robot, world
```bash
ros2 launch robot_base robot_base.launch.py gazebo:=true
```

### With RViz2 auto-launched
```bash
ros2 launch robot_base robot_base.launch.py gazebo:=true use_rviz:=true
```

### Custom robot URDF

Place your URDF file inside your project first (recommended
for portability), then pass its path :

```bash
ros2 launch robot_base robot_base.launch.py gazebo:=true \
    urdf_path:=/absolute/path/to/my_robot.urdf
```

### Custom world file
```bash
ros2 launch robot_base robot_base.launch.py gazebo:=true \
    world_file:=/absolute/path/to/robot_world.world
```

### Custom spawn position and orientation
```bash
ros2 launch robot_base robot_base.launch.py gazebo:=true \
    x_pose:=2.0 \
    y_pose:=1.0 \
    yaw:=1.57
```

### Slower robot (useful for tight spaces)
```bash
ros2 launch robot_base robot_base.launch.py gazebo:=true \
    max_linear_vel:=0.2 \
    max_angular_vel:=0.3
```

### Two robots at different positions
```bash
# Terminal 1 — first robot
ros2 launch robot_base robot_base.launch.py gazebo:=true \
    robot_name:=robot_1 x_pose:=0.0 y_pose:=0.5

# Terminal 2 — second robot
ros2 launch robot_base robot_base.launch.py \
    robot_name:=robot_2 x_pose:=0.0 y_pose:=-0.5
```

### Full custom setup
```bash
ros2 launch robot_base robot_base.launch.py gazebo:=true \
    robot_name:=my_robot            \
    urdf_path:=/path/to/robot.urdf  \
    world_file:=/path/to/world.world \
    x_pose:=1.0                     \
    y_pose:=2.0                     \
    yaw:=3.14                       \
    max_linear_vel:=0.3             \
    max_angular_vel:=0.5            \
    use_rviz:=true
```

---

## Standalone build and run

```bash
# 1. Create symlink from kit to your project workspace
ln -s ~/robotics/robotics-toolkit/kit/robot_base \
      ~/your_project/robot_ws/src/robot_base

# 2. Build
cd ~/your_project/robot_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select robot_base --symlink-install

# 3. Source
source install/setup.bash

# 4. Launch
ros2 launch robot_base robot_base.launch.py gazebo:=true
```

---

## Reuse in a parent launch file

```python
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare

robot_base = IncludeLaunchDescription(
    PythonLaunchDescriptionSource([
        FindPackageShare('robot_base'),
        '/launch/robot_base.launch.py'
    ]),
    launch_arguments={
        'robot_name':     'robot_1',
        'urdf_path':      '/path/to/robot.urdf',
        'world_file':     '/path/to/robot_world.world',
        'x_pose':         '0.0',
        'y_pose':         '0.0',
        'use_rviz':       'false',
        'max_linear_vel': '0.5',
    }.items()
)
```

---

## Configuration file (`config/default_params.yaml`)

Fine-grained parameters are in `config/default_params.yaml`.
Edit this file to tune the robot behavior without touching code.

Key parameters :

| Parameter | Default | Description |
|-----------|---------|-------------|
| `robot_name` | `robot_000` | Robot identifier |
| `max_linear_velocity` | `0.5` m/s | Speed limit |
| `max_angular_velocity` | `1.0` rad/s | Rotation limit |
| `wheel_radius` | `0.05` m | Must match URDF |
| `wheel_separation` | `0.34` m | Must match URDF |
| `status_publish_rate` | `1.0` Hz | Status publish frequency |

---

## Default robot description

The built-in robot is a differential-drive AMR with :
- Rectangular chassis : 40cm × 30cm × 10cm
- Two drive wheels (radius 5cm)
- One passive front caster wheel
- 360° LiDAR (10m range, 1° resolution, gaussian noise)
- Front-mounted RGB camera (640×480, 60° FOV, 30 FPS)

To use a different robot, pass `urdf_path` with your own
URDF/Xacro file. The rest of the module works unchanged.