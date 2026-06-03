import os
from glob import glob
from setuptools import setup

PACKAGE_NAME = 'robot_bringup'

setup(
    name=PACKAGE_NAME,
    version='0.1.0',
    packages=[PACKAGE_NAME],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + PACKAGE_NAME]),
        ('share/' + PACKAGE_NAME, ['package.xml']),
        # Launch files
        (os.path.join('share', PACKAGE_NAME, 'launch'),
            glob('launch/*.py')),
        # Config files
        (os.path.join('share', PACKAGE_NAME, 'config'),
            glob('config/*.yaml')),
        # World files
        (os.path.join('share', PACKAGE_NAME, 'worlds'),
            glob('worlds/*.world')),
        # Map files
        (os.path.join('share', PACKAGE_NAME, 'maps'),
            glob('maps/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Kossi',
    maintainer_email='sd.cosmos.1812@gmail.com',
    description='AMR project bringup — orchestrates all kit modules',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': []},
)