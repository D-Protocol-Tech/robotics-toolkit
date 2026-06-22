"""
============================================================
FILE        : map_manager.py
MODULE      : slam_module (kit/)
DESCRIPTION : Map save/load manager node.

WHAT IT DOES:
    Provides ROS 2 services to save and load maps:
        /slam/save_map  → saves current map to disk as .pgm + .yaml
        /slam/load_map  → loads a saved map from disk

    Also monitors map quality and logs statistics.

WHY THIS EXISTS:
    slam_toolbox can save maps but requires knowing the right
    service names and parameters. This node wraps that into
    a clean, consistent interface reusable across projects.

SERVICES:
    /slam/save_map  (std_srvs/srv/Trigger) → saves current map
    /slam/load_map  (std_srvs/srv/Trigger) → loads saved map

TOPICS:
    Subscribes : /map  (nav_msgs/OccupancyGrid) → map statistics
    Publishes  : /slam/status (std_msgs/String)  → JSON status

REUSABILITY:
    Change map_file_path in slam_params.yaml to save maps
    anywhere on the filesystem.
============================================================
"""

import os
import json
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import String
from std_srvs.srv import Trigger
from slam_toolbox.srv import DeserializePoseGraph


class MapManager(Node):
    """
    Manages map persistence (save/load) and monitors map quality.
    """

    def __init__(self):
        super().__init__('map_manager')

        # --------------------------------------------------
        # PARAMETERS
        # --------------------------------------------------
        self.declare_parameter('map_directory', '')
        self.declare_parameter('map_filename', 'house_map')
        self.declare_parameter('status_rate', 1.0)   # Hz

        map_dir = self.get_parameter('map_directory').value
        map_name = self.get_parameter('map_filename').value
        status_rate = self.get_parameter('status_rate').value

        if not map_dir:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            map_dir = os.path.abspath(os.path.join(current_dir, '..', 'maps'))

        self.map_file_path = os.path.join(map_dir, map_name)

        # --------------------------------------------------
        # INTERNAL STATE
        # --------------------------------------------------
        self.map_width = 0
        self.map_height = 0
        self.map_resolution = 0.0
        self.explored_cells = 0    # cells with known value (not -1)
        self.total_cells = 0
        self.map_received = False

        # --------------------------------------------------
        # SUBSCRIBER: /map
        # slam_toolbox publishes the growing map here
        # --------------------------------------------------
        self.map_sub = self.create_subscription(
            OccupancyGrid,
            '/map',
            self._on_map,
            10
        )

        # --------------------------------------------------
        # PUBLISHER: /slam/status
        # --------------------------------------------------
        self.status_pub = self.create_publisher(
            String, '/slam/status', 10
        )

        # --------------------------------------------------
        # SERVICES
        # --------------------------------------------------

        # /slam/save_map — call this when exploration is done
        self.save_srv = self.create_service(
            Trigger,
            '/slam/save_map',
            self._handle_save_map
        )

        # /slam/load_map — call this when map file is provide
        self.load_srv = self.create_service(
            Trigger, '/slam/load_map', self._handle_load_map
        )

        self.slam_toolbox_client = self.create_client(
            DeserializePoseGraph, '/slam_toolbox/deserialize_map'
        )

        # --------------------------------------------------
        # TIMER: status publisher
        # --------------------------------------------------
        self.timer = self.create_timer(
            1.0 / status_rate,
            self._publish_status
        )

        self.get_logger().info(
            f'MapManager ready | '
            f'map will be saved to: {self.map_file_path}'
        )

    # ----------------------------------------------------------
    # CALLBACK: map update received
    # ----------------------------------------------------------
    def _on_map(self, msg: OccupancyGrid):
        """
        Called every time slam_toolbox updates the map.
        Computes exploration statistics from the OccupancyGrid.

        OccupancyGrid values:
          -1  = unknown (unexplored)
           0  = free space
          100 = occupied (wall/obstacle)
        """
        self.map_received = True
        self.map_width = msg.info.width
        self.map_height = msg.info.height
        self.map_resolution = msg.info.resolution
        self.total_cells = self.map_width * self.map_height

        # Count cells that have been explored (value != -1)
        self.explored_cells = sum(
            1 for cell in msg.data if cell != -1
        )

    # ----------------------------------------------------------
    # SERVICE HANDLER: save map
    # ----------------------------------------------------------
    def _handle_save_map(
        self, request: Trigger.Request, response: Trigger.Response
    ):
        """
        Saves the current map using slam_toolbox's map saver.
        Called when the /slam/save_map service is triggered.
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(self.map_file_path), exist_ok=True)

            # Call ROS 2 map_saver_cli to save the map
            # This generates two files: .pgm (image) + .yaml (metadata)
            save_cmd = (
                f'ros2 run nav2_map_server map_saver_cli '
                f'-f {self.map_file_path} '
                f'--ros-args -p use_sim_time:=true'
            )
            exit_code = os.system(save_cmd)

            if exit_code == 0:
                response.success = True
                response.message = f'Map saved to {self.map_file_path}.pgm'
                self.get_logger().info(response.message)
            else:
                response.success = False
                response.message = f'Map save failed (exit code {exit_code})'
                self.get_logger().error(response.message)

        except Exception as e:
            response.success = False
            response.message = f'Map save error: {str(e)}'
            self.get_logger().error(response.message)

        return response
    
    # ----------------------------------------------------------
    # SERVICE HANDLER: LOAD MAP
    # ----------------------------------------------------------
    def _handle_load_map(self, request: Trigger.Request, response: Trigger.Response):
        """Loads a saved map via slam_toolbox deserialization service."""

        target_map_path = self.map_file_path

        self.get_logger().info(f'Attempting to load map from: {target_map_path}')

        # Checking for the existence of files before shutting down the system
        if not os.path.exists(f"{target_map_path}.yaml"):
            response.success = False
            response.message = f'Load failed: File {target_map_path}.yaml not found.'
            self.get_logger().error(response.message)
            return response

        # Wait for the slam_toolbox service to be available
        if not self.slam_toolbox_client.wait_for_service(timeout_sec=5.0):
            response.success = False
            response.message = 'Service /slam_toolbox/deserialize_map not available.'
            self.get_logger().error(response.message)
            return response

        # Preparation of the request for slam_toolbox
        slam_req = DeserializePoseGraph.Request()
        slam_req.filename = target_map_path
        slam_req.match_type = DeserializePoseGraph.Request.START_AT_FIRST_NODE

        # Simplified synchronous call for the service manager
        future = self.slam_toolbox_client.call_async(slam_req)
        
        # Note technique : Dans un callback de service ROS 2, faire un spin_until_future_complete 
        # provoquerait un blocage (deadlock). On utilise une boucle d'attente légère ou une exécution directe.
        while rclpy.ok() and not future.done():
            pass 

        try:
            slam_res = future.result()
            # slam_toolbox uses a return code (0 = SUCCESS)
            if slam_res is not None:
                response.success = True
                response.message = f'Map {target_map_path} successfully loaded into slam_toolbox.'
                self.get_logger().info(response.message)
            else:
                response.success = False
                response.message = 'Slam_toolbox returned an empty response during loading.'
                self.get_logger().error(response.message)
        except Exception as e:
            response.success = False
            response.message = f'Error loading the map : {str(e)}'
            self.get_logger().error(response.message)

        return response

    # ----------------------------------------------------------
    # TIMER CALLBACK: publish status
    # ----------------------------------------------------------
    def _publish_status(self):
        """Publishes SLAM and map statistics as JSON."""

        if self.total_cells > 0:
            explored_pct = (self.explored_cells / self.total_cells) * 100
        else:
            explored_pct = 0.0

        status = {
            "map_received": self.map_received,
            "map_width": self.map_width,
            "map_height": self.map_height,
            "resolution_m": self.map_resolution,
            "explored_pct": round(explored_pct, 1),
            "explored_cells": self.explored_cells,
            "total_cells": self.total_cells,
        }

        msg = String()
        msg.data = json.dumps(status)
        self.status_pub.publish(msg)


def main(args=None):
    """Entry point — ros2 run slam_module map_manager"""
    rclpy.init(args=args)
    node = MapManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
