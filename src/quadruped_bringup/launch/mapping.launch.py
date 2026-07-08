import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    bringup_share = get_package_share_directory('quadruped_bringup')

    # Chaine de perception commune (TF lidar, odom_to_tf, pointcloud_to_laserscan)
    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'sensors.launch.py')
        )
    )

    # slam_toolbox en mode mapping : construit la carte a partir de /scan_synced
    slam = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        parameters=[os.path.join(bringup_share, 'config', 'slam_config.yaml')],
    )

    return LaunchDescription([
        sensors,
        slam,
    ])
