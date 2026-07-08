import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def launch_setup(context, *args, **kwargs):
    robot = LaunchConfiguration('robot').perform(context)
    profile_path = os.path.join(
        get_package_share_directory('quadruped_bringup'), 'profiles', f'{robot}.yaml')

    # Pont /cmd_vel -> SDK Unitree (specifique B2). Pour un autre robot,
    # remplacer ce noeud par l'adapter equivalent exposant le meme contrat
    # /cmd_vel (Twist) -> API hardware, voir README.
    robot_adapter = Node(
        package='quadruped_adapter',
        executable='robot_adapter',
        name='robot_adapter',
        parameters=[profile_path],
    )

    return [robot_adapter]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='b2',
            description='Profil robot a charger (profiles/<robot>.yaml)'),
        OpaqueFunction(function=launch_setup),
    ])
