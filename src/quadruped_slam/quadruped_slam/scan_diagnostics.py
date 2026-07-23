import math
import time
from collections import deque
from threading import Lock
from typing import Deque, Optional, Sequence

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan, PointCloud2


def _stamp_to_seconds(sec: int, nanosec: int) -> float:
    return float(sec) + float(nanosec) * 1e-9


def _format(value: Optional[float]) -> str:
    if value is None:
        return 'n/a'
    return f'{value:.6f}'


class ScanDiagnostics(Node):
    def __init__(self) -> None:
        super().__init__('scan_diagnostics')
        self._lock = Lock()
        self._cloud_group = ReentrantCallbackGroup()
        self._scan_group = ReentrantCallbackGroup()
        self._timer_group = ReentrantCallbackGroup()

        self._cloud_count = 0
        self._scan_count = 0
        self._cloud_monotonicity_violations = 0
        self._scan_monotonicity_violations = 0
        self._cloud_last_stamp: Optional[float] = None
        self._scan_last_stamp: Optional[float] = None
        self._cloud_window_times: Deque[float] = deque(maxlen=64)
        self._scan_window_times: Deque[float] = deque(maxlen=128)
        self._cloud_intervals: Deque[float] = deque(maxlen=64)
        self._scan_intervals: Deque[float] = deque(maxlen=128)
        self._scan_finite_ratio: Optional[float] = None
        self._scan_inf_ratio: Optional[float] = None
        self._scan_min_range: Optional[float] = None
        self._scan_max_range: Optional[float] = None
        self._scan_ray_count: Optional[int] = None
        self._scan_age: Optional[float] = None
        self._scan_frame: Optional[str] = None
        self._cloud_age: Optional[float] = None
        self._cloud_frame: Optional[str] = None

        scan_qos = QoSProfile(depth=20, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(
            PointCloud2,
            '/rslidar_points',
            self._cloud_callback,
            qos_profile_sensor_data,
            callback_group=self._cloud_group,
        )
        self.create_subscription(
            LaserScan,
            '/scan_synced',
            self._scan_callback,
            scan_qos,
            callback_group=self._scan_group,
        )
        self.create_timer(2.0, self._report, callback_group=self._timer_group)

    @staticmethod
    def _frequency(times: Deque[float]) -> Optional[float]:
        if len(times) < 2:
            return None
        duration = times[-1] - times[0]
        if duration <= 0.0:
            return None
        return (len(times) - 1) / duration

    def _cloud_callback(self, msg: PointCloud2) -> None:
        now = time.monotonic_ns() * 1e-9
        stamp = _stamp_to_seconds(msg.header.stamp.sec, msg.header.stamp.nanosec)
        with self._lock:
            self._cloud_count += 1
            self._cloud_window_times.append(now)
            if self._cloud_last_stamp is not None:
                self._cloud_intervals.append(stamp - self._cloud_last_stamp)
                if stamp <= self._cloud_last_stamp:
                    self._cloud_monotonicity_violations += 1
            self._cloud_last_stamp = stamp
            self._cloud_age = now - stamp if math.isfinite(stamp) else None
            self._cloud_frame = msg.header.frame_id or '<empty>'

    def _scan_callback(self, msg: LaserScan) -> None:
        now = time.monotonic_ns() * 1e-9
        stamp = _stamp_to_seconds(msg.header.stamp.sec, msg.header.stamp.nanosec)
        finite_count = 0
        inf_count = 0
        min_range = None
        max_range = None
        for value in msg.ranges:
            if math.isfinite(value):
                finite_count += 1
                min_range = value if min_range is None else min(min_range, value)
                max_range = value if max_range is None else max(max_range, value)
            elif math.isinf(value):
                inf_count += 1
        ray_count = len(msg.ranges)
        with self._lock:
            self._scan_count += 1
            self._scan_window_times.append(now)
            if self._scan_last_stamp is not None:
                self._scan_intervals.append(stamp - self._scan_last_stamp)
                if stamp <= self._scan_last_stamp:
                    self._scan_monotonicity_violations += 1
            self._scan_last_stamp = stamp
            self._scan_age = now - stamp if math.isfinite(stamp) else None
            self._scan_frame = msg.header.frame_id or '<empty>'
            if ray_count > 0:
                self._scan_finite_ratio = finite_count / ray_count
                self._scan_inf_ratio = inf_count / ray_count
            else:
                self._scan_finite_ratio = None
                self._scan_inf_ratio = None
            self._scan_min_range = min_range
            self._scan_max_range = max_range
            self._scan_ray_count = ray_count

    def _report(self) -> None:
        with self._lock:
            cloud_count = self._cloud_count
            scan_count = self._scan_count
            cloud_freq = self._frequency(deque(self._cloud_window_times, maxlen=self._cloud_window_times.maxlen))
            scan_freq = self._frequency(deque(self._scan_window_times, maxlen=self._scan_window_times.maxlen))
            cloud_last = self._cloud_last_stamp
            scan_last = self._scan_last_stamp
            cloud_age = self._cloud_age
            scan_age = self._scan_age
            cloud_frame = self._cloud_frame
            scan_frame = self._scan_frame
            cloud_monotonicity = self._cloud_monotonicity_violations
            scan_monotonicity = self._scan_monotonicity_violations
            scan_ray_count = self._scan_ray_count
            scan_finite_ratio = self._scan_finite_ratio
            scan_inf_ratio = self._scan_inf_ratio
            scan_min_range = self._scan_min_range
            scan_max_range = self._scan_max_range
            scan_intervals = list(self._scan_intervals)
            cloud_intervals = list(self._cloud_intervals)

        self.get_logger().info('========== SCAN DIAGNOSTICS ==========')
        self.get_logger().info('PointCloud2:')
        self.get_logger().info(f'  topic: /rslidar_points')
        self.get_logger().info(f'  total messages: {cloud_count}')
        self.get_logger().info(f'  frequency: {_format(cloud_freq)} Hz')
        self.get_logger().info(f'  frame_id: {cloud_frame or "n/a"}')
        self.get_logger().info(f'  latest stamp: {_format(cloud_last)}')
        self.get_logger().info(f'  message age: {_format(cloud_age)} s')
        self.get_logger().info(f'  monotonicity violations: {cloud_monotonicity}')
        self.get_logger().info(
            f'  delta between clouds: {_format(cloud_intervals[-1] if cloud_intervals else None)} s'
        )
        self.get_logger().info('LaserScan:')
        self.get_logger().info(f'  topic: /scan_synced')
        self.get_logger().info(f'  total messages: {scan_count}')
        self.get_logger().info(f'  frequency: {_format(scan_freq)} Hz')
        self.get_logger().info(f'  frame_id: {scan_frame or "n/a"}')
        self.get_logger().info(f'  latest stamp: {_format(scan_last)}')
        self.get_logger().info(f'  message age: {_format(scan_age)} s')
        self.get_logger().info(f'  monotonicity violations: {scan_monotonicity}')
        self.get_logger().info(
            f'  delta between scans: {_format(scan_intervals[-1] if scan_intervals else None)} s'
        )
        self.get_logger().info(f'  ray count: {scan_ray_count if scan_ray_count is not None else "n/a"}')
        self.get_logger().info(f'  finite ratio: {_format(scan_finite_ratio)}')
        self.get_logger().info(f'  inf ratio: {_format(scan_inf_ratio)}')
        self.get_logger().info(f'  min observed range: {_format(scan_min_range)} m')
        self.get_logger().info(f'  max observed range: {_format(scan_max_range)} m')
        self.get_logger().info('======================================')


def main(args: Optional[Sequence[str]] = None) -> None:
    rclpy.init(args=args)
    node = ScanDiagnostics()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.remove_node(node)
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
