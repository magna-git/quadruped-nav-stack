# Debugging — Erreurs et Solutions

## Problème 1 : serdata.cpp:384 — String data is not null-terminated

**Symptôme** : `/rslidar_points` publie mais `/scan` ne se produit jamais. Les topics natifs Unitree disparaissent en Wi-Fi.

**Cause** : Build custom de `rmw_cyclonedds_cpp` dans `~/slam_config/cyclonedds_go2_B2_ws` cassé. Config CycloneDDS ne couvrait que eth0, pas Wi-Fi.

**Solution** : 
- Utiliser le paquet standard `ros-humble-rmw-cyclonedds-cpp` (apt)
- Config DDS dual-interface : eth0 + wlp62s0 en même temps

**Fichiers** :
- `scripts/dds/cyclonedds_dual_interface.xml` — config avec les deux interfaces
- `scripts/env/setup_env.sh` — sourcer ça avant de lancer ROS2

**À faire** : `source scripts/env/setup_env.sh` puis `ros2 launch ...`

