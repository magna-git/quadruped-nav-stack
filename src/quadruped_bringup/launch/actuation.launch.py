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
    #
    # Force fastrtps pour ce node (au lieu du cyclonedds du reste du stack) :
    # rclcpp::init cree un domain participant cyclonedds implicite (domaine 0)
    # quand RMW_IMPLEMENTATION=rmw_cyclonedds_cpp, qui entre en conflit avec le
    # domain participant explicite cree par ChannelFactory::Instance()->Init()
    # du SDK Unitree (meme domaine, meme processus) -> crash
    # 'PreconditionNotMetError - Failed to create domain explicitly'. En
    # fastrtps, rclcpp ne cree pas de participant cyclonedds donc pas de
    # conflit avec le SDK. Les topics simples (/cmd_vel) restent interoperables
    # entre RMW differents.
    robot_adapter = Node(
        package='quadruped_adapter',
        executable='robot_adapter',
        name='robot_adapter',
        parameters=[profile_path],
        additional_env={'RMW_IMPLEMENTATION': 'rmw_fastrtps_cpp'},
    )

    return [robot_adapter]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='b2',
            description='Profil robot a charger (profiles/<robot>.yaml)'),
        OpaqueFunction(function=launch_setup),
    ])
