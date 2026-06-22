import os
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from example_interfaces.srv import SetString

class WorldManager(Node):
    """
    Gère les fichiers de mondes disponibles pour la simulation 
    et expose des informations sur l'environnement actuel.
    """
    def __init__(self):
        super().__init__('world_manager')

        # PARAMÈTRES
        self.declare_parameter('worlds_directory', '')
        self.declare_parameter('current_world', 'empty.world')

        self.worlds_dir = self.get_parameter('worlds_directory').value
        self.current_world = self.get_parameter('current_world').value

        # Si aucun dossier n'est fourni, on cherche le dossier 'worlds' du package share
        if not self.worlds_dir:
            # En Python ROS2, le chemin d'exécution peut varier, on s'appuie sur une structure standard
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.worlds_dir = os.path.abspath(os.path.join(current_dir, '..', 'worlds'))

        # PUBLISHER: Statut de la simulation (JSON)
        self.status_pub = self.create_publisher(String, '/simulation/status', 10)
        self.timer = self.create_timer(2.0, self._publish_status)

        # SERVICE: Changer virtuellement de référence de monde (Utile pour la supervision)
        self.srv_set_world = self.create_service(
            SetString, '/simulation/set_active_world', self._handle_set_world
        )

        self.get_logger().info(f"WorldManager initialisé. Dossier des mondes : {self.worlds_dir}")

    def _get_available_worlds(self):
        """Scane le dossier et liste tous les fichiers .world ou .sdf"""
        if not os.path.exists(self.worlds_dir):
            return []
        return [f for f in os.listdir(self.worlds_dir) if f.endswith(('.world', '.sdf'))]

    def _publish_status(self):
        """Publie les informations de simulation sous format JSON"""
        status = {
            "current_world": self.current_world,
            "worlds_directory": self.worlds_dir,
            "available_worlds": self._get_available_worlds()
        }
        msg = String()
        msg.data = json.dumps(status)
        self.status_pub.publish(msg)

    def _handle_set_world(self, request, response):
        """Change le nom du monde actif (attention, ne recharge pas Gazebo en direct)"""
        requested_world = request.data.strip()
        available = self._get_available_worlds()

        if requested_world not in available:
            response.success = False
            response.message = f"Échec : {requested_world} introuvable dans le dossier."
            self.get_logger().error(response.message)
            return response

        self.current_world = requested_world
        response.success = True
        response.message = f"Monde actif défini sur : {self.current_world}"
        self.get_logger().info(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = WorldManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()