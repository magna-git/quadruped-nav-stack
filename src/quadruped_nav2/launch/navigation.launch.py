import glob
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def _latest_map(maps_dir: str) -> str:
    candidates = glob.glob(os.path.join(maps_dir, '*.yaml'))
    if not candidates:
        raise RuntimeError(
            f"Aucune carte (.yaml) trouvee dans {maps_dir}. "
            "Sauvegarde-en une d'abord avec map_saver_cli, ou passe map:=<chemin>."
        )
    return max(candidates, key=os.path.getmtime)


def launch_setup(context, *args, **kwargs):
    robot = LaunchConfiguration('robot').perform(context)
    use_rviz = LaunchConfiguration('use_rviz')
    bringup_share = get_package_share_directory('quadruped_bringup')
    nav2_share = get_package_share_directory('quadruped_nav2')

    # map:='' (defaut) -> on prend automatiquement la derniere carte sauvegardee
    # (par date de modification) dans le dossier maps/ installe du package.
    # Rappel : apres un map_saver_cli dans src/quadruped_bringup/maps/, il faut
    # un `colcon build --symlink-install` pour qu'elle apparaisse ici.
    map_yaml_file = LaunchConfiguration('map').perform(context)
    if not map_yaml_file:
        map_yaml_file = _latest_map(os.path.join(bringup_share, 'maps'))

    params_file = LaunchConfiguration('params_file').perform(context)
    if not params_file:
        params_file = os.path.join(nav2_share, 'config', f'nav2_params_{robot}.yaml')

    # Perception + actuation (memes chaines que le mapping, mais sans slam_toolbox :
    # AMCL se localise sur la carte statique deja construite)
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

    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_share, 'launch', 'localization.launch.py')
        ),
        launch_arguments={
            'robot': robot,
            'map': map_yaml_file,
            'params_file': params_file,
            'use_rviz': 'false',
        }.items(),
    )

    # -- Groupe navigation (planif globale, evitement d'obstacles, waypoints) --
    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        parameters=[params_file],
        remappings=[('cmd_vel', 'cmd_vel_nav')],
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        parameters=[params_file],
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        parameters=[params_file],
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        parameters=[params_file],
    )

    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        parameters=[params_file],
    )

    # Lisse la sortie du controller_server avant /cmd_vel, lu par
    # quadruped_adapter (robot_adapter.cpp) demarre via actuation.launch.py.
    velocity_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        parameters=[params_file],
        remappings=[('cmd_vel', 'cmd_vel_nav'), ('cmd_vel_smoothed', 'cmd_vel')],
    )

    lifecycle_manager_navigation = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        parameters=[params_file],
    )
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_navigation',
        arguments=['-d', LaunchConfiguration('rviz_config')],
        condition=IfCondition(use_rviz),
    )

    return [
        sensors,
        actuation,
        localization,
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        velocity_smoother,
        lifecycle_manager_navigation,
        rviz,
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='b2',
            description='Profil robot (profiles/<robot>.yaml + nav2_params_<robot>.yaml)'),
        DeclareLaunchArgument(
            'map', default_value='',
            description='Carte statique (.yaml) ; vide = la plus recente dans maps/'),
        DeclareLaunchArgument(
            'params_file', default_value='',
            description='Fichier nav2 a utiliser ; vide = config/nav2_params_<robot>.yaml'),
        DeclareLaunchArgument('use_rviz', default_value='false'),
        DeclareLaunchArgument(
            'rviz_config',
            default_value='/home/unitree/unified_nav_ws/rviz/navigation.rviz',
        ),
        OpaqueFunction(function=launch_setup),
    ])
