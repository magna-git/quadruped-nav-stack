from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Chaine de perception commune, partagee entre mapping et navigation.

    robot_center --(TF statique)--> rslidar --(odom_to_tf)--> odom
    puis rslidar_points --(pointcloud_to_laserscan)--> /scan_synced
    """

    # 1. TF statique robot_center -> rslidar
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'robot_center', 'rslidar'],
        name='static_tf_lidar'
    )

    # 2. odom_to_tf + re-stamp du scan
    odom_to_tf = Node(
        package='quadruped_bringup',
        executable='odom_to_tf',
        name='odom_to_tf'
    )

    # 3. pointcloud_to_laserscan (obstacles pour les costmaps nav2)
    pc_to_scan = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[('cloud_in', '/rslidar_points')],
        parameters=[{
            'target_frame': 'rslidar',
            'min_height': -0.3,
            'max_height': 0.5,
            'use_inf': True,
        }]
    )

    return LaunchDescription([
        static_tf,
        odom_to_tf,
        pc_to_scan,
    ])
