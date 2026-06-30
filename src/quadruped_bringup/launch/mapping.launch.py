import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    # 1. TF statique robot_center → rslidar
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'robot_center', 'rslidar'],
        name='static_tf_lidar'
    )

    # 2. odom_to_tf + scan re-stamper
    odom_to_tf = Node(
        package='quadruped_bringup',
        executable='odom_to_tf',
        name='odom_to_tf'
    )

    # 3. pointcloud_to_laserscan
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

    # 4. slam_toolbox
    slam = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        parameters=[os.path.join(
            get_package_share_directory('quadruped_bringup'),
            'config', 'slam_config.yaml'
        )],
    )

    return LaunchDescription([
        static_tf,
        odom_to_tf,
        pc_to_scan,
        slam,
    ])
