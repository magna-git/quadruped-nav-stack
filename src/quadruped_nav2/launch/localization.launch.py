import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    robot = LaunchConfiguration('robot').perform(context)
    use_rviz = LaunchConfiguration('use_rviz')
    nav2_share = get_package_share_directory('quadruped_nav2')

    params_file = LaunchConfiguration('params_file').perform(context)
    if not params_file:
        params_file = os.path.join(nav2_share, 'config', f'nav2_params_{robot}.yaml')

    map_yaml_file = LaunchConfiguration('map').perform(context)

    return [
        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            parameters=[params_file, {'yaml_filename': map_yaml_file}],
        ),
        Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            parameters=[params_file],
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_localization',
            parameters=[params_file],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2_localization',
            arguments=['-d', LaunchConfiguration('rviz_config')],
            condition=IfCondition(use_rviz),
        ),
    ]


def generate_launch_description():
    nav2_share = get_package_share_directory('quadruped_nav2')
    return LaunchDescription([
        DeclareLaunchArgument('robot', default_value='b2'),
        DeclareLaunchArgument('map'),
        DeclareLaunchArgument('params_file', default_value=''),
        DeclareLaunchArgument('use_rviz', default_value='false'),
        DeclareLaunchArgument(
            'rviz_config',
            default_value='/home/unitree/unified_nav_ws/rviz/navigation.rviz',
        ),
        OpaqueFunction(function=launch_setup),
    ])
