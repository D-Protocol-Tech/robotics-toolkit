"""
============================================================
FILE        : setup.py
MODULE      : robot_base (kit/)
DESCRIPTION : Package installation configuration.

colcon reads this file to know how to install the package.
data_files is critical: it copies YAML, URDF, and launch
files into install/ so ROS 2 can find them at runtime.
============================================================
"""

import os
from glob import glob
from setuptools import setup

PACKAGE_NAME = 'robot_base'

setup(
    name=PACKAGE_NAME,
    version='0.1.0',
    packages=[PACKAGE_NAME],
    data_files=[
        # Required: registers package in ROS 2 index
        ('share/ament_index/resource_index/packages',
            ['resource/' + PACKAGE_NAME]),
        # Required: package manifest
        ('share/' + PACKAGE_NAME, ['package.xml']),
        # Launch files
        (os.path.join('share', PACKAGE_NAME, 'launch'),
            glob('launch/*.py')),
        # Config files
        (os.path.join('share', PACKAGE_NAME, 'config'),
            glob('config/*.yaml')),
        # URDF / Xacro files
        (os.path.join('share', PACKAGE_NAME, 'urdf'),
            glob('urdf/*')),
        # 3D mesh files (empty for now, ready for future use)
        (os.path.join('share', PACKAGE_NAME, 'meshes'),
            glob('meshes/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Kossivi',
    maintainer_email='sd.cosmos.1812@gmail.com',
    description='Robot base module — reusable across ROS 2 projects',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # ros2 run robot_base base_controller
            'base_controller = robot_base.base_controller:main',
            # ros2 run robot_base robot_state_publisher
            'robot_state_publisher = robot_base.robot_state_publisher:main',
        ],
    },
)
