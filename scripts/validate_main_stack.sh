#!/usr/bin/env bash
set -euo pipefail

pass() { echo "PASS | $1"; }
warn() { echo "WARN | $1"; }
fail() { echo "FAIL | $1"; }

topic_exists() {
  ros2 topic list 2>/dev/null | grep -qx "$1"
}

topic_type_is() {
  local actual
  actual="$(ros2 topic type "$1" 2>/dev/null || true)"
  [[ "$actual" == "$2" ]]
}

node_exists() {
  ros2 node list 2>/dev/null | grep -qx "$1"
}

check_tf() {
  local target="$1"
  local source="$2"
  if timeout 3s ros2 run tf2_ros tf2_echo "$target" "$source" >/tmp/tf_check.$$ 2>&1; then
    pass "TF $target -> $source"
  else
    warn "TF $target -> $source unavailable"
  fi
  rm -f /tmp/tf_check.$$
}

topic_exists /rslidar_points && pass "topic /rslidar_points present" || fail "topic /rslidar_points missing"
topic_exists /dog_odom && pass "topic /dog_odom present" || fail "topic /dog_odom missing"
topic_exists /scan_synced && pass "topic /scan_synced present" || warn "topic /scan_synced missing"
topic_exists /map && pass "topic /map present" || warn "topic /map missing"
topic_exists /cmd_vel && pass "topic /cmd_vel present" || warn "topic /cmd_vel missing"

topic_type_is /rslidar_points sensor_msgs/msg/PointCloud2 && pass "/rslidar_points type OK" || warn "/rslidar_points type mismatch"
topic_type_is /dog_odom nav_msgs/msg/Odometry && pass "/dog_odom type OK" || warn "/dog_odom type mismatch"
topic_type_is /scan_synced sensor_msgs/msg/LaserScan && pass "/scan_synced type OK" || warn "/scan_synced type mismatch"

check_tf map odom
check_tf odom robot_center
check_tf robot_center rslidar
check_tf robot_center dog_imu_link
check_tf dog_imu_link rslidar

for node_name in /slam_toolbox /map_server /amcl /controller_server /planner_server /bt_navigator /waypoint_follower /velocity_smoother; do
  node_exists "$node_name" && pass "node $node_name present" || warn "node $node_name absent"
done

for lifecycle_node in map_server amcl controller_server planner_server behavior_server bt_navigator waypoint_follower velocity_smoother; do
  if ros2 lifecycle get "/$lifecycle_node" >/tmp/lifecycle.$$ 2>&1; then
    pass "lifecycle /$lifecycle_node reachable"
  else
    warn "lifecycle /$lifecycle_node unreachable"
  fi
done
rm -f /tmp/lifecycle.$$

for action_name in /navigate_to_pose /navigate_through_poses /follow_waypoints; do
  if ros2 action list 2>/dev/null | grep -qx "$action_name"; then
    pass "action $action_name present"
  else
    warn "action $action_name absent"
  fi
done
