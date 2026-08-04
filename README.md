# quadruped-nav-stack

The `main` branch corresponds to the first experimental generation of the navigation stack. Its initial pipeline was:

```text
LiDAR PointCloud2
→ PointCloud filtering
→ LaserScan conversion
→ slam_toolbox
→ 2D mapping experiments
```

This version was used for initial validation. Some mapping robustness limitations were observed due to LiDAR noise and scan quality. The project was later reorganized into a generic multi-robot architecture.

For the current architecture, installation instructions and robot integration workflow, refer to the `refactor/reorganize-repository` branch.
