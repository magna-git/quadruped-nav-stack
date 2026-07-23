import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    robot = LaunchConfiguration('robot').perform(context)
    use_rviz = LaunchConfiguration('use_rviz')
    start_actuation = LaunchConfiguration('start_actuation').perform(context)
    bringup_share = get_package_share_directory('quadruped_bringup')
    slam_share = get_package_share_directory('quadruped_slam')

    slam_params_file = LaunchConfiguration('slam_params_file').perform(context)
    if not slam_params_file:
        slam_params_file = os.path.join(slam_share, 'config', 'slam_toolbox_mapping.yaml')

    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'sensors.launch.py')
        ),
        launch_arguments={'robot': robot}.items(),
    )

    actions = [sensors]
    if start_actuation.lower() == 'true':
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(bringup_share, 'launch', 'actuation.launch.py')
                ),
                launch_arguments={'robot': robot}.items(),
            )
        )

    actions.append(
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            parameters=[slam_params_file, {'use_sim_time': LaunchConfiguration('use_sim_time')}],
        )
    )
    actions.append(
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2_mapping',
            arguments=['-d', LaunchConfiguration('rviz_config')],
            condition=IfCondition(use_rviz),
        )
    )
    return actions


def generate_launch_description():
    slam_share = get_package_share_directory('quadruped_slam')
    return LaunchDescription([
        DeclareLaunchArgument('robot', default_value='b2'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('start_actuation', default_value='true'),
        DeclareLaunchArgument('slam_params_file', default_value=''),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=os.path.join(slam_share, 'rviz', 'mapping.rviz'),
        ),
        OpaqueFunction(function=launch_setup),
    ])
