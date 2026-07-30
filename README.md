# AMR ROS 2 Toolkit 🤖

Flotte de Robots Mobiles Autonomes simulée avec ROS 2 Humble + Gazebo.

## Architecture modulaire

Ce projet est conçu comme une **boîte à outils réutilisable**.
Chaque module dans `src/` est indépendant et peut être extrait
dans un autre projet ROS 2 sans modification majeure.

## Modules disponibles

| Module | Description | Réutilisable |
|--------|-------------|--------------|
| `robot_base` | URDF robot, capteurs, simulation Gazebo | ✅ |
| `sensor_interface` | Abstraction LiDAR / Caméra / IMU | ✅ |
| `slam_module` | Cartographie SLAM temps réel | ✅ |
| `nav2_config` | Navigation autonome Nav2 | ✅ |
| `obstacle_avoidance` | Évitement obstacles dynamiques | ✅ |
| `mission_planner` | File de missions A→B | ✅ |
| `qr_navigator` | Détection QR + repérage sol | ✅ |
| `object_detector` | Détection objets YOLO temps réel | ✅ |
| `vision_bridge` | Pipeline OpenCV → ROS 2 topics | ✅ |
| `fleet_manager` | Orchestration flotte N robots | ✅ |
| `collision_manager` | Anti-collision inter-robots | ✅ |

## Prérequis

- Ubuntu 22.04 (natif ou WSL2)
- ROS 2 Humble
- Gazebo Classic 11
- Python 3.10+

## Installation rapide

```bash
# Cloner le repo
git clone https://github.com/D-Protocol-Tech/amr-ros2-toolkit.git
cd amr-ros2-toolkit

# Installer les dépendances
rosdep install --from-paths src --ignore-src -r -y

# Compiler
colcon build

# Sourcer
source install/setup.bash
```

## Versions

- `v0.1` — Environnement + structure projet
- `v0.2` — Robot de base + simulation Gazebo  
- `v0.3` — SLAM + cartographie
- `v0.4` — Navigation autonome Nav2
- `v0.5` — Vision IA (QR + YOLO)
- `v1.0` — Flotte multi-robots complète
