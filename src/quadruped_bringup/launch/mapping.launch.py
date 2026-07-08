import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def launch_setup(context, *args, **kwargs):
    robot = LaunchConfiguration('robot').perform(context)
    bringup_share = get_package_share_directory('quadruped_bringup')

    # Chaine de perception + actuation (teleop possible pendant le mapping)
    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'sensors.launch.py')
        ),
        launch_arguments={'robot': robot}.items(),
    )
    actuation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'actuation.launch.py')
        ),
        launch_arguments={'robot': robot}.items(),
    )

    # slam_toolbox en mode mapping : construit la carte a partir de /scan_synced
    slam = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        parameters=[os.path.join(bringup_share, 'config', f'slam_config_{robot}.yaml')],
    )

    return [sensors, actuation, slam]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='b2',
            description='Profil robot (profiles/<robot>.yaml + config/slam_config_<robot>.yaml)'),
        OpaqueFunction(function=launch_setup),
    ])
