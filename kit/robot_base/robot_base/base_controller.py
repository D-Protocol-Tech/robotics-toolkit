"""
============================================================
FILE        : base_controller.py
MODULE      : robot_base (kit/)
DESCRIPTION : Base controller node for the robot.

WHAT IT DOES:
    - Subscribes to /cmd_vel to receive velocity commands
    - Publishes robot status on /robot_status
    - Enforces velocity safety limits from config
    - Logs odometry data for debugging

    In simulation, actual wheel movement is handled by
    the Gazebo diff_drive plugin. This node adds the
    safety layer and status reporting on top.

TOPICS:
    Subscribes : /cmd_vel    (geometry_msgs/Twist)
    Subscribes : /odom       (nav_msgs/Odometry)
    Publishes  : /robot_status (std_msgs/String)

REUSABILITY:
    All limits and topic names come from default_params.yaml.
    Drop this node into any differential-drive robot project.
============================================================
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String
import json


class BaseController(Node):
    """
    Safety layer and status monitor for the robot base.

    Sits between the navigation stack and Gazebo:
        Nav2 → /cmd_vel → BaseController (safety check) → Gazebo
    """

    def __init__(self):
        super().__init__('base_controller')

        # --------------------------------------------------
        # PARAMETERS (all from default_params.yaml)
        # --------------------------------------------------
        self.declare_parameter('robot_name', 'robot_000')
        self.declare_parameter('max_linear_velocity', 0.5)
        self.declare_parameter('max_angular_velocity', 1.0)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('status_publish_rate', 1.0)

        # Read parameter values into local variables
        self.robot_name = self.get_parameter('robot_name').value
        self.max_linear = self.get_parameter('max_linear_velocity').value
        self.max_angular = self.get_parameter('max_angular_velocity').value
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        odom_topic = self.get_parameter('odom_topic').value
        status_rate = self.get_parameter('status_publish_rate').value

        # --------------------------------------------------
        # INTERNAL STATE
        # --------------------------------------------------
        self.current_linear_vel = 0.0   # m/s
        self.current_angular_vel = 0.0   # rad/s
        self.position_x = 0.0   # meters from start
        self.position_y = 0.0
        self.total_commands = 0     # counter for diagnostics

        # --------------------------------------------------
        # SUBSCRIBERS
        # --------------------------------------------------

        # /cmd_vel — receives velocity commands from Nav2 or teleop
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            cmd_vel_topic,
            self._on_cmd_vel,    # callback function
            10                   # queue depth: keep last 10 messages
        )

        # /odom — receives position estimates from Gazebo diff_drive
        self.odom_sub = self.create_subscription(
            Odometry,
            odom_topic,
            self._on_odom,
            10
        )

        # --------------------------------------------------
        # PUBLISHERS
        # --------------------------------------------------

        # /robot_status — publishes a JSON status string
        # Other modules (dashboard, fleet_manager) can subscribe
        self.status_pub = self.create_publisher(String, '/robot_status', 10)

        # --------------------------------------------------
        # TIMER: publish status at fixed rate
        # --------------------------------------------------
        self.status_timer = self.create_timer(
            1.0 / status_rate,   # period in seconds
            self._publish_status
        )

        self.get_logger().info(
            f'BaseController ready — robot: {self.robot_name} | '
            f'max linear: {self.max_linear} m/s | '
            f'max angular: {self.max_angular} rad/s'
        )

    # ----------------------------------------------------------
    # CALLBACK: /cmd_vel received
    # ----------------------------------------------------------
    def _on_cmd_vel(self, msg: Twist):
        """
        Called every time a velocity command arrives.

        Clamps the velocities to safe limits before
        storing them. The clamped values are what Gazebo
        actually executes (via the diff_drive plugin).
        """
        self.total_commands += 1

        # math.clamp equivalent: keep value within [−max, +max]
        raw_linear = msg.linear.x
        raw_angular = msg.angular.z

        # Clamp to safety limits
        clamped_linear = max(-self.max_linear,
                             min(self.max_linear, raw_linear))
        clamped_angular = max(-self.max_angular,
                              min(self.max_angular, raw_angular))

        self.current_linear_vel = clamped_linear
        self.current_angular_vel = clamped_angular

        # Warn if a command was clamped (useful for debugging)
        if raw_linear != clamped_linear or raw_angular != clamped_angular:
            self.get_logger().warn(
                f'Velocity clamped: '
                f'linear {raw_linear:.2f}→{clamped_linear:.2f} m/s | '
                f'angular {raw_angular:.2f}→{clamped_angular:.2f} rad/s'
            )

    # ----------------------------------------------------------
    # CALLBACK: /odom received
    # ----------------------------------------------------------
    def _on_odom(self, msg: Odometry):
        """
        Called every time an odometry message arrives.
        Stores the current position for status reporting.
        """
        self.position_x = msg.pose.pose.position.x
        self.position_y = msg.pose.pose.position.y

    # ----------------------------------------------------------
    # TIMER CALLBACK: publish status
    # ----------------------------------------------------------
    def _publish_status(self):
        """
        Publishes a JSON status string at regular intervals.

        JSON format allows any subscriber (dashboard, fleet_manager,
        logging system) to parse the data easily.
        """
        status = {
            "robot_name": self.robot_name,
            "linear_vel": round(self.current_linear_vel, 3),
            "angular_vel": round(self.current_angular_vel, 3),
            "position_x": round(self.position_x, 3),
            "position_y": round(self.position_y, 3),
            "total_cmds": self.total_commands,
        }

        msg = String()
        msg.data = json.dumps(status)   # dict → JSON string
        self.status_pub.publish(msg)


def main(args=None):
    """Entry point — called by: ros2 run robot_base base_controller"""
    rclpy.init(args=args)
    node = BaseController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
