# Main Stack Initial Audit

Date: 2026-07-23
Branch: `main`

## Architecture Initiale Trouvee

- Le mapping 2D existe deja, mais il est porte par `quadruped_bringup`, pas par un package dedie `quadruped_slam`.
- `pointcloud_to_laserscan` est lance depuis `quadruped_bringup/launch/sensors.launch.py`.
- `slam_toolbox` en mode mapping est lance depuis `quadruped_bringup/launch/mapping.launch.py`.
- `odom -> robot_center` est publie par `quadruped_bringup/quadruped_bringup/odom_to_tf.py`.
- `robot_center -> rslidar` est publie par `static_transform_publisher`.
- `robot_center -> dog_imu_link` n'est pas publie dans les launchs audites.
- La navigation lance directement perception, actuation, `map_server`, `amcl`, Nav2 et `velocity_smoother` depuis `quadruped_nav2/launch/navigation.launch.py`.

## Publishers TF Identifies

- `robot_center -> rslidar`
  - `tf2_ros/static_transform_publisher` dans `quadruped_bringup/launch/sensors.launch.py`
- `robot_center -> dog_imu_link`
  - aucun publisher trouve dans les launchs actuels
- `odom -> robot_center`
  - `quadruped_bringup/odom_to_tf.py`
- `map -> odom` en mapping
  - `slam_toolbox`
- `map -> odom` en localisation
  - attendu de `amcl`, mais pas de launch de localisation dedie present

## Topics Et Parametres Actuels

- Entree LiDAR 3D: `/rslidar_points`
- Sortie `pointcloud_to_laserscan`: `/scan`
- Scan restampe utilisable par le stack: `/scan_synced`
- Odometrie: `/dog_odom`
- Commande vitesse: `/cmd_vel`

### Parametres SLAM Reels Charges

Fichier: `src/quadruped_bringup/config/slam_config_b2.yaml`

- `map_frame: map`
- `odom_frame: odom`
- `base_frame: robot_center`
- `scan_topic: /scan_synced`
- `transform_timeout: 2.5`
- `tf_buffer_duration: 30.0`

### Parametres Nav2 Reels Charges

Fichier: `src/quadruped_nav2/config/nav2_params_b2.yaml`

- AMCL en `robot_center`, `odom`, `map`
- `scan_topic: /scan_synced`
- modele AMCL holonome (`OmniMotionModel`)
- controller `nav2_graceful_controller::GracefulController`
- costmaps basees sur `/scan_synced`
- sortie lissee `cmd_vel_nav -> cmd_vel`

## Problemes Confirmes

- Aucun package `quadruped_slam` n'existe sur `main`.
- Aucun launch de localisation dedie n'existe.
- La TF `robot_center -> dog_imu_link` manque dans le stack stable.
- `odom_to_tf.py` couple la republication `scan -> scan_synced` et la publication TF.
- La configuration `pointcloud_to_laserscan` n'est pas exposee de facon complete ni documentee.
- Aucun script reproductible de sauvegarde de carte n'existe.
- Aucun script global de validation du stack n'existe.
- Aucun jeu RViz stable mapping/navigation n'existe.

## Problemes Seulement Suspectes

- Parametres costmap et footprint a confirmer physiquement.
- Qualite reelle du LaserScan 2D issu du LiDAR 3D non encore validee par un diagnostic dedie.
- Risque de robustesse insuffisante du pipeline si la carte est incomplete ou si les scans sont mal filtres.

## Fichiers Dupliques Ou Obsoletes

- `src/quadruped_nav2/config/nav2_params_b2_DWB_backup.yaml`
- Documentation racine utile, mais workflow mapping/localisation/navigation encore trop melange.
