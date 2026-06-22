"""
============================================================
FILE        : mission_client.py
MODULE      : nav2_config (kit/)
DESCRIPTION : Navigation mission client node.

WHAT IT DOES:
    Provides a clean Python API to send navigation goals
    to Nav2 and monitor their execution.

    Instead of dealing with Nav2 action servers directly,
    other modules just call:
        client.go_to(x=3.0, y=2.0, yaw=0.0)

WHY THIS EXISTS:
    Nav2 uses ROS 2 Actions (more complex than topics/services).
    This node wraps that complexity into a simple interface
    reusable by mission_planner, fleet_manager, etc.

TOPICS/ACTIONS:
    Action client : /navigate_to_pose (nav2_msgs/NavigateToPose)
    Publishes     : /nav/status (std_msgs/String) JSON status

REUSABILITY:
    Import MissionClient in any module that needs to send
    navigation goals. No Nav2 knowledge required.
============================================================
"""

import json
import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String, Bool
from action_msgs.msg import GoalStatus


class MissionClient(Node):
    """
    Clean interface to Nav2 navigation stack.
    Sends goals and monitors execution status.
    """

    # Navigation status constants — readable names
    STATUS_IDLE = "idle"
    STATUS_NAVIGATING = "navigating"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    def __init__(self):
        super().__init__('mission_client')

        # --------------------------------------------------
        # PARAMETERS
        # --------------------------------------------------
        self.declare_parameter('robot_name', 'robot_000')
        self.declare_parameter('goal_timeout', 30.0)    # seconds

        self.robot_name = self.get_parameter('robot_name').value
        self.goal_timeout = self.get_parameter('goal_timeout').value

        # --------------------------------------------------
        # INTERNAL STATE
        # --------------------------------------------------
        self.status = self.STATUS_IDLE
        self.current_goal_x = 0.0
        self.current_goal_y = 0.0
        self.goals_completed = 0
        self.goals_failed = 0
        self._goal_handle = None
        self.goal_start_time = None

        # --------------------------------------------------
        # ACTION CLIENT: Nav2 NavigateToPose
        # --------------------------------------------------
        self._nav_client = ActionClient(
            self,
            NavigateToPose,
            f'/{self.robot_name}/navigate_to_pose'
        )

        # --------------------------------------------------
        # PUBLISHER: navigation status
        # --------------------------------------------------
        self.status_pub = self.create_publisher(
            String, f'/{self.robot_name}/nav/status', 10
        )

        self.get_logger().info(
            f'MissionClient ready — robot: {self.robot_name}'
        )

        # --------------------------------------------------
        # SUBSCRIBER: /goal_pose (from RViz2 "2D Goal Pose")
        # RViz2 publishes here when user clicks on the map
        # --------------------------------------------------
        self.goal_sub = self.create_subscription(
            PoseStamped,
            f'/{self.robot_name}/goal_pose',
            self._on_goal_pose,
            10
        )

        # Sécurité : Écoute un éventuel arrêt d'urgence
        self.estop_sub = self.create_subscription(
            Bool,
            f'/{self.robot_name}/emergency_stop',
            self._on_emergency_stop,
            10
        )

        # --------------------------------------------------
        # TIMER: publish status & check timeout (1Hz)
        # --------------------------------------------------
        self.timer = self.create_timer(1.0, self._on_timer_tick)
        self.get_logger().info(f'Listening for goals on /{self.robot_name}/goal_pose...')

    def go_to(self, x: float, y: float, yaw: float = 0.0):
        """
        Send a navigation goal to Nav2.

        Args:
            x   : target X position in map frame (meters)
            y   : target Y position in map frame (meters)
            yaw : target orientation (radians, 0 = facing +X)

        Returns:
            True if goal was accepted, False otherwise.

        Example:
            client.go_to(x=3.0, y=2.0, yaw=0.0)
        """
        # Wait for Nav2 action server to be available
        if not self._nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error(
                'Nav2 action server not available. '
                'Is navigation stack running?'
            )
            return False

        # Build goal message
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self._build_pose_stamped(x, y, yaw)

        self.get_logger().info(
            f'Sending goal to {self.robot_name} '
            f'x={x:.2f}, y={y:.2f}, yaw={yaw:.2f}'
        )

        # Starting the timer before sending
        self.goal_start_time = self.get_clock().now()

        # Send goal asynchronously
        send_goal_future = self._nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self._on_feedback
        )
        send_goal_future.add_done_callback(self._on_goal_response)

        self.status = self.STATUS_NAVIGATING
        self.current_goal_x = x
        self.current_goal_y = y
        return True

    def cancel_goal(self):
        """Cancel the current navigation goal."""
        if self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
            self.status = self.STATUS_CANCELLED
            self.goal_start_time = None
            self.get_logger().info('Goal actively cancelled')

    # ----------------------------------------------------------
    # PRIVATE: action callbacks
    # ----------------------------------------------------------
    def _on_goal_pose(self, msg: PoseStamped):
        """
        Called when RViz2 publishes a 2D Goal Pose.
        Extracts x, y from the message and sends to Nav2.
        """
        x = msg.pose.position.x
        y = msg.pose.position.y

        # Extract yaw from quaternion
        qz = msg.pose.orientation.z
        qw = msg.pose.orientation.w
        yaw = 2.0 * math.atan2(qz, qw)

        self.get_logger().info(
            f'Goal received from RViz2: '
            f'x={x:.2f}, y={y:.2f}, yaw={yaw:.2f}'
        )
        self.go_to(x=x, y=y, yaw=yaw)

    def _on_emergency_stop(self, msg: Bool):
        """Triggers immediate stop if True is received on the E-Stop topic."""
        if msg.data and self.status == self.STATUS_NAVIGATING:
            self.get_logger().warn(
                f'!!! EMERGENCY STOP RECEIVED FOR {self.robot_name} !!!'
            )
            self.cancel_goal()

    def _on_goal_response(self, future):
        """Called when Nav2 accepts or rejects our goal."""
        self._goal_handle = future.result()

        if not self._goal_handle.accepted:
            self.get_logger().error('Goal rejected by Nav2')
            self.status = self.STATUS_FAILED
            self.goals_failed += 1
            self.goal_start_time = None
            return

        self.get_logger().info('Goal accepted by Nav2 — navigating...')

        # Register result callback
        result_future = self._goal_handle.get_result_async()
        result_future.add_done_callback(self._on_result)

    def _on_feedback(self, feedback_msg):
        """
        Called periodically during navigation.
        feedback contains distance_remaining.
        """
        distance = feedback_msg.feedback.distance_remaining
        self.get_logger().info(
            f'{self.robot_name} -> Distance remaining: {distance:.2f} m',
            throttle_duration_sec=2.0  # log max once every 2 seconds
        )

    def _on_result(self, future):
        """Called when navigation goal completes (success or failure)."""
        result = future.result()
        self.goal_start_time = None

        if result.status == GoalStatus.STATUS_SUCCEEDED:
            self.status = self.STATUS_SUCCEEDED
            self.goals_completed += 1
            self.get_logger().info(
                f'Goal reached successfully by {self.robot_name}! '
                f'({self.current_goal_x:.2f}, {self.current_goal_y:.2f})'
            )
        else:
            self.status = self.STATUS_FAILED
            self.goals_failed += 1
            self.get_logger().warn(
                f'Goal failed with status: {result.status} by {self.robot_name}'
            )

    def _build_pose_stamped(
        self, x: float, y: float, yaw: float
    ) -> PoseStamped:
        """
        Builds a PoseStamped message from x, y, yaw.
        Converts yaw (radians) to quaternion for ROS 2.
        """
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()

        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0

        # Convert yaw angle to quaternion
        # For 2D navigation, only Z and W components matter
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)

        return pose

    # ----------------------------------------------------------
    # TIMED MONITORING & STATUS
    # ----------------------------------------------------------
    def _on_timer_tick(self):
        """Fired every second to publish status and enforce safety timeouts."""
        # 1. Gestion du Timeout
        if self.status == self.STATUS_NAVIGATING and self.goal_start_time is not None:
            # Calcul du temps écoulé en secondes
            now = self.get_clock().now()
            elapsed_sec = (now - self.goal_start_time).nanoseconds / 1e9

            if elapsed_sec > self.goal_timeout:
                self.get_logger().error(
                    f'[TIMEOUT] Robot {self.robot_name} exceeded limit of {self.goal_timeout}s! Cancelling mission.'
                )
                self.goals_failed += 1
                self.cancel_goal()

        # 2. Publication du rapport d'état
        self._publish_status()

    def _publish_status(self):
        """Publishes navigation status as JSON."""
        status = {
            "robot_name": self.robot_name,
            "nav_status": self.status,
            "goal_x": self.current_goal_x,
            "goal_y": self.current_goal_y,
            "goals_completed": self.goals_completed,
            "goals_failed": self.goals_failed,
        }
        msg = String()
        msg.data = json.dumps(status)
        self.status_pub.publish(msg)


def main(args=None):
    """Entry point — ros2 run nav2_config mission_client"""
    rclpy.init(args=args)
    node = MissionClient()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
