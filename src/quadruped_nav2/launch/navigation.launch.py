import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    bringup_share = get_package_share_directory('quadruped_bringup')
    nav2_share = get_package_share_directory('quadruped_nav2')

    default_map = os.path.join(bringup_share, 'maps', 'innov8_map.yaml')
    default_params = os.path.join(nav2_share, 'config', 'nav2_params.yaml')

    map_yaml_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')

    declare_map = DeclareLaunchArgument(
        'map', default_value=default_map,
        description='Carte statique (.yaml) sur laquelle AMCL se localise')

    declare_params = DeclareLaunchArgument(
        'params_file', default_value=default_params,
        description='Fichier de parametres nav2 (amcl, DWB, costmaps, waypoints...)')

    # Chaine de perception commune (TF lidar, odom_to_tf, pointcloud_to_laserscan)
    # -> alimente AMCL et les costmaps en /scan_synced, sans relancer slam_toolbox.
    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'sensors.launch.py')
        )
    )

    # -- Groupe localisation --
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        parameters=[params_file, {'yaml_filename': map_yaml_file}],
    )

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        parameters=[params_file],
    )

    lifecycle_manager_localization = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        parameters=[params_file],
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

    # Lisse la sortie du controller_server avant de l'envoyer sur /cmd_vel,
    # c'est ce topic final que lit quadruped_adapter (robot_adapter.cpp).
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

    return LaunchDescription([
        declare_map,
        declare_params,
        sensors,
        map_server,
        amcl,
        lifecycle_manager_localization,
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        velocity_smoother,
        lifecycle_manager_navigation,
    ])
