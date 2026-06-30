import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped

class OdomToTF(Node):
    def __init__(self):
        super().__init__('odom_to_tf')
        self.br = TransformBroadcaster(self)

        qos_odom = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.sub_odom = self.create_subscription(
            Odometry, '/dog_odom', self.odom_cb, qos_odom)

        qos_scan = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.sub_scan = self.create_subscription(
            LaserScan, '/scan', self.scan_cb, qos_scan)
        self.pub_scan = self.create_publisher(LaserScan, '/scan_synced', 10)

        self.get_logger().info('odom_to_tf + scan re-stamper demarre')

    def odom_cb(self, msg):
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
    rclpy.spin(OdomToTF())

if __name__ == '__main__':
    main()
