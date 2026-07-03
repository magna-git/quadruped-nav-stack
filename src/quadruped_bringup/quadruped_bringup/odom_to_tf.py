#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped


class OdomToTF(Node):
    def __init__(self):
        super().__init__('odom_to_tf')
        self.br = TransformBroadcaster(self)

        # Callback groups separes : odom_cb (500Hz) et scan_cb ne se bloquent
        # plus mutuellement sur le meme thread -> fini la famine de scan_cb.
        odom_group = MutuallyExclusiveCallbackGroup()
        scan_group = MutuallyExclusiveCallbackGroup()

        qos_odom = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.sub_odom = self.create_subscription(
            Odometry, '/dog_odom', self.odom_cb, qos_odom,
            callback_group=odom_group)

        qos_scan = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.sub_scan = self.create_subscription(
            LaserScan, '/scan', self.scan_cb, qos_scan,
            callback_group=scan_group)

        self.pub_scan = self.create_publisher(LaserScan, '/scan_synced', 10)

        # Throttle du broadcast TF : 500Hz est inutile pour SLAM/Nav2 (qui
        # tournent a 10-30Hz). On limite a 50Hz pour retirer la pression sur
        # l'executor et laisser scan_cb s'executer regulierement.
        self.tf_period_sec = 1.0 / 50.0
        self._last_tf_time_sec = 0.0

        self.get_logger().info(
            'odom_to_tf + scan re-stamper demarre (multi-thread, TF throttled a 50Hz)')

    def odom_cb(self, msg):
        now_sec = self.get_clock().now().nanoseconds * 1e-9
        if now_sec - self._last_tf_time_sec < self.tf_period_sec:
            return
        self._last_tf_time_sec = now_sec

        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = msg.header.frame_id
        t.child_frame_id = msg.child_frame_id
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation
        self.br.sendTransform(t)

    def scan_cb(self, msg):
        msg.header.stamp = self.get_clock().now().to_msg()
        self.pub_scan.publish(msg)


def main():
    rclpy.init()
    node = OdomToTF()
    # 2 threads : un pour chaque callback group, pour qu'ils tournent
    # vraiment en parallele au lieu de se sequencer.
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()