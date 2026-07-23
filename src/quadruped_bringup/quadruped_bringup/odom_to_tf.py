#!/usr/bin/env python3
import copy
import math
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
        self.declare_parameter('odom_topic', '/dog_odom')
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('scan_synced_topic', '/scan_synced')
        odom_topic = self.get_parameter('odom_topic').value
        scan_topic = self.get_parameter('scan_topic').value
        scan_synced_topic = self.get_parameter('scan_synced_topic').value
        self.br = TransformBroadcaster(self)
        odom_group = MutuallyExclusiveCallbackGroup()
        scan_group = MutuallyExclusiveCallbackGroup()
        qos_odom = QoSProfile(depth=100, reliability=ReliabilityPolicy.BEST_EFFORT)
        qos_scan = QoSProfile(depth=20, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.sub_odom = self.create_subscription(
            Odometry,
            odom_topic,
            self.odom_cb,
            qos_odom,
            callback_group=odom_group
        )
        self.sub_scan = self.create_subscription(
            LaserScan,
            scan_topic,
            self.scan_cb,
            qos_scan,
            callback_group=scan_group
        )
        self.pub_scan = self.create_publisher(LaserScan, scan_synced_topic, 10)
        self._last_odom_msg = None
        self.get_logger().info(
            'odom_to_tf v4: TF 2D (Z=0, yaw only) et scan_synced publies'
        )

    def odom_cb(self, msg: Odometry):
        self._last_odom_msg = msg

    def publish_tf(self, stamp):
        msg = self._last_odom_msg
        if msg is None:
            return False
        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = msg.header.frame_id or 'odom'
        t.child_frame_id = msg.child_frame_id or 'robot_center'
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = 0.0
        q = msg.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = math.sin(yaw / 2.0)
        t.transform.rotation.w = math.cos(yaw / 2.0)
        self.br.sendTransform(t)
        return True

    def scan_cb(self, msg: LaserScan):
        if self._last_odom_msg is None:
            return
        stamp = self.get_clock().now().to_msg()
        self.publish_tf(stamp)
        synced = copy.deepcopy(msg)
        synced.header.stamp = stamp
        synced.header.frame_id = msg.header.frame_id or 'rslidar'
        self.pub_scan.publish(synced)

def main():
    rclpy.init()
    node = OdomToTF()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
