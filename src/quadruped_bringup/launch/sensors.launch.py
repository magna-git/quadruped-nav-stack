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

    lidar_xyz = [str(value) for value in params['lidar_tf_xyz']]
    lidar_rpy = [str(value) for value in params['lidar_tf_rpy']]
    imu_xyz = [str(value) for value in params['imu_tf_xyz']]
    imu_rpy = [str(value) for value in params['imu_tf_rpy']]

    # 1. TF statiques du robot : LiDAR et IMU vers la base.
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=lidar_xyz + lidar_rpy + [params['base_frame'], params['target_frame']],
        name='static_tf_lidar'
    )
    static_tf_imu = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=imu_xyz + imu_rpy + [params['base_frame'], params['imu_frame']],
        name='static_tf_imu'
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

    return [static_tf, static_tf_imu, odom_to_tf, pc_to_scan]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='b2',
            description='Profil robot a charger (profiles/<robot>.yaml)'),
        OpaqueFunction(function=launch_setup),
    ])
