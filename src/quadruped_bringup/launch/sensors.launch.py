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


def _standard_rmw_env() -> dict:
    # Le build custom rmw_cyclonedds_cpp (~/slam_config/cyclonedds_go2_B2_ws)
    # a un bug de deserialisation des champs string imbriques (PointField[]
    # dans PointCloud2) qui fait taire pointcloud_to_laserscan sans erreur
    # visible cote nav2/amcl (voir TESTS_DEMAIN.md section 6). On force donc
    # ce node a resoudre rmw_cyclonedds_cpp via le paquet standard apt en le
    # retirant de son LD_LIBRARY_PATH/AMENT_PREFIX_PATH, sans toucher au
    # reste du stack qui garde le build custom (utilise potentiellement par
    # le SDK bas niveau Unitree).
    custom_ws = os.path.join(os.path.expanduser('~'), 'slam_config', 'cyclonedds_go2_B2_ws')
    overrides = {}
    for var in ('LD_LIBRARY_PATH', 'AMENT_PREFIX_PATH'):
        parts = os.environ.get(var, '').split(':')
        overrides[var] = ':'.join(p for p in parts if p and not p.startswith(custom_ws))
    return overrides


def launch_setup(context, *args, **kwargs):
    robot = LaunchConfiguration('robot').perform(context)
    profile_path, params = _load_profile(robot)

   # 1. TF statique base -> lidar. Offset provisoire repris de l'URDF officiel
    # Unitree (b2_description/xacro/robot.xacro, joint lidar_joint, trunk -> lidar_link) :
    # xyz="0.34218 0 0.17851", rpy="0 0 0". NON calibre sur notre rslidar (LiDAR
    # tiers, position physique possiblement differente) - a verifier en RViz avant
    # de faire confiance a cette valeur pour du SLAM/nav reel. Voir TESTS_DEMAIN.md.
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0.34218', '0', '0.17851', '0', '0', '0', params['base_frame'], params['target_frame']],
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
        additional_env=_standard_rmw_env(),
    )

    return [static_tf, odom_to_tf, pc_to_scan]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='b2',
            description='Profil robot a charger (profiles/<robot>.yaml)'),
        OpaqueFunction(function=launch_setup),
    ])
