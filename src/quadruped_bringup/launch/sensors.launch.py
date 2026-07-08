import os
import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def _load_profile(robot: str) -> dict:
    profile_path = os.path.join(
        get_package_share_directory('quadruped_bringup'), 'profiles', f'{robot}.yaml')
    with open(profile_path) as f:
        data = yaml.safe_load(f)
    return profile_path, data['/**']['ros__parameters']


def launch_setup(context, *args, **kwargs):
    robot = LaunchConfiguration('robot').perform(context)
    profile_path, params = _load_profile(robot)

    # 1. TF statique base -> lidar. Offset physique reel non calibre (TODO,
    # voir TESTS_DEMAIN.md) : identite pour l'instant.
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', params['base_frame'], params['target_frame']],
        name='static_tf_lidar'
    )

    # 2. odom_to_tf + re-stamp du scan (topics pilotes par le profil robot)
    odom_to_tf = Node(
        package='quadruped_bringup',
        executable='odom_to_tf',
        name='odom_to_tf',
        parameters=[profile_path],
    )

    # 3. pointcloud_to_laserscan (obstacles pour les costmaps nav2)
    pc_to_scan = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[('cloud_in', params['lidar_topic'])],
        parameters=[profile_path],
    )

    return [static_tf, odom_to_tf, pc_to_scan]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='b2',
            description='Profil robot a charger (profiles/<robot>.yaml)'),
        OpaqueFunction(function=launch_setup),
    ])
