# quadruped-nav-stack

## Project overview

`quadruped-nav-stack` is a ROS 2 workspace for LiDAR perception, SLAM, localization, and Nav2 navigation on quadruped robots. The architecture is robot-independent where possible: shared ROS behavior stays in the packages, while topics, frames, motion limits, SLAM parameters, Nav2 parameters, and hardware adapters provide the robot-specific integration.

The ROS 2 distribution depends on the robot platform. The B2 integration currently targets ROS 2 Humble; Go2 support is being tested with ROS 2 Jazzy. Use packages matching the distribution installed on the target robot.

## Workspace packages

| Package | Purpose |
| --- | --- |
| `quadruped_bringup` | Robot profiles, sensor conversion, TF publication, SLAM configuration, maps, and mapping/actuation launch files. |
| `quadruped_nav2` | Nav2 localization, planning, control, obstacle avoidance, velocity smoothing, and waypoint following. |
| `quadruped_adapter` | Hardware boundary that converts ROS `geometry_msgs/Twist` commands into Unitree B2 SDK motion calls. |

## ROS pipeline

The perception and navigation path is:

```text
LiDAR PointCloud2
→ pointcloud_to_laserscan
→ /scan
→ timestamp synchronization (/scan_synced) and TF publication
→ slam_toolbox (mapping) or AMCL + Nav2 (navigation)
→ /cmd_vel_nav
→ velocity_smoother
→ /cmd_vel
→ quadruped_adapter
→ robot SDK
```

`sensors.launch.py` loads the selected robot profile, publishes the static base-to-LiDAR transform, runs `odom_to_tf`, and converts the configured PointCloud2 topic to LaserScan. Mapping consumes `/scan_synced` with SLAM Toolbox. Navigation loads a static map, localizes with AMCL, and uses Nav2 to plan and produce velocity commands.

## Launch files

| Launch file | Command | What it starts |
| --- | --- | --- |
| `sensors.launch.py` | `ros2 launch quadruped_bringup sensors.launch.py robot:=b2` | Sensor conversion, scan synchronization, and TF publication. |
| `actuation.launch.py` | `ros2 launch quadruped_bringup actuation.launch.py robot:=b2` | The configured hardware adapter. |
| `mapping.launch.py` | `ros2 launch quadruped_bringup mapping.launch.py robot:=b2` | Sensors, actuation, and asynchronous SLAM Toolbox. |
| `navigation.launch.py` | `ros2 launch quadruped_nav2 navigation.launch.py robot:=b2` | Sensors, actuation, map server, AMCL, and the Nav2 servers. |

All launch files default to `robot:=b2`. Navigation also accepts `map:=/path/to/map.yaml` and `params_file:=/path/to/nav2_params.yaml`.

## Installation and build

Install the ROS 2 distribution appropriate for the robot, then install the workspace dependencies:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

`requirements.txt` lists the required ROS system packages for the current Humble-based B2 setup. It is an apt package reference, not a Python `pip` requirements file; for another ROS distribution, install the equivalent packages for that distribution.

The Unitree SDK 2 is not vendored in this repository. Install it separately using Unitree's SDK instructions, then expose its root directory before building:

```bash
export UNITREE_SDK_DIR=/path/to/unitree_sdk2
colcon build --symlink-install
source install/setup.bash
```

If `UNITREE_SDK_DIR` is not set, the build looks in `$HOME/unitree_sdk2`. It can also be supplied with `colcon build --cmake-args -DUNITREE_SDK_DIR=/path/to/unitree_sdk2`.

Before launching, source the appropriate DDS environment script for the network configuration, followed by the workspace:

```bash
source scripts/env/setup_env.sh
source install/setup.bash
```

## Mapping workflow

1. Select a robot profile and confirm its LiDAR topic, odometry topic, frames, network interface, and safety limits.
2. Build and source the workspace.
3. Start mapping:

   ```bash
   ros2 launch quadruped_bringup mapping.launch.py robot:=b2
   ```

4. Drive the robot through the environment while monitoring the map and TF tree in RViz.
5. Save the completed map into the bringup package:

   ```bash
   ros2 run nav2_map_server map_saver_cli -f src/quadruped_bringup/maps/<map_name>
   ```

6. Rebuild so the saved `.yaml` and image are installed into the package share directory:

   ```bash
   colcon build --symlink-install
   source install/setup.bash
   ```

## Navigation workflow

Start navigation with a specific map:

```bash
ros2 launch quadruped_nav2 navigation.launch.py robot:=b2 map:=/absolute/path/to/map.yaml
```

If `map` is omitted, `navigation.launch.py` selects the most recently modified `.yaml` map installed under `quadruped_bringup/maps`. The launch starts the sensor and actuation chains, map server, AMCL, planner, controller, behavior server, behavior-tree navigator, waypoint follower, velocity smoother, and lifecycle managers. Set the initial pose and navigation goals in RViz after AMCL and the Nav2 lifecycle nodes are active.

## Hardware adapter and `/cmd_vel`

`quadruped_adapter` is the hardware-specific boundary for the current B2 integration. Its `robot_adapter` node subscribes to the profile's `cmd_vel_topic` (normally `/cmd_vel`), clamps `linear.x`, `linear.y`, and `angular.z` to the configured limits, and converts them to Unitree B2 `SportClient::Move` calls. A watchdog stops the robot when commands become stale.

Nav2 publishes controller output on `/cmd_vel_nav`; the velocity smoother publishes the final command on `/cmd_vel`. For a robot from another vendor, replace the adapter with an implementation that accepts the same `geometry_msgs/Twist` contract and translates it to that robot's SDK or control API.

## Integrating another robot

Robots are integrated through profiles and configuration files, not long-lived robot branches. Add and validate:

- `src/quadruped_bringup/profiles/<robot>.yaml` for topics, frames, network settings, and motion limits;
- `src/quadruped_bringup/config/slam_config_<robot>.yaml` for SLAM Toolbox;
- `src/quadruped_nav2/config/nav2_params_<robot>.yaml` for Nav2;
- a compatible hardware adapter when the robot does not use the current Unitree B2 SDK interface.

Keep frame names consistent across all three configuration files, then launch with `robot:=<robot>`. Robot support should be added to the shared architecture instead of creating a separate branch per platform.

## Future web and API integration

The ROS packages are intended to remain the runtime core while a future web/API layer can expose status, maps, missions, and navigation commands to external applications without coupling the user interface to a specific robot SDK.
