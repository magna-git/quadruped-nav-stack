#!/bin/bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/dds/cyclonedds_dual_interface.xml"
export ROS_DOMAIN_ID=0
