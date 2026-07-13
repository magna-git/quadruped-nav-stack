# Plan de test — B2-W nav stack

## 0. Corrige depuis la derniere session (a re-verifier, pas encore teste en vrai)

- [x] `quadruped_adapter` est maintenant lance automatiquement via
      `actuation.launch.py`, inclus par `mapping.launch.py` et
      `navigation.launch.py`. Plus besoin de le demarrer a la main.
- [x] `teleop.py` publie par defaut sur `/cmd_vel` (aligne avec
      `robot_adapter` et la sortie nav2).
- [x] `profiles/b2.yaml` deplace dans `quadruped_bringup` et reellement
      charge (odom_to_tf, pointcloud_to_laserscan, robot_adapter) au lieu
      d'etre un doc mort.
- [x] `quadruped_slam` (package vide, sans rapport avec le vrai pipeline
      SLAM) supprime.

Reste ouvert :
- [ ] TF statique `robot_center -> rslidar` = identite (0,0,0,0,0,0) dans
      `sensors.launch.py` — a verifier/calibrer contre le vrai montage du LiDAR.
- [x] BUG BLOQUANT identifie le 2026-07-13 : `pointcloud_to_laserscan` ne
      publiait jamais sur `/scan` (voir section 6) — CORRIGE le 2026-07-13,
      voir section 7 pour le fix et sa validation.
- [ ] Carte `b2_map_2026-07-10` trop peu exploree (~84% unknown) + couple
      `robot_radius`/`inflation_radius` sans doute trop serre pour l'espace
      dispo — bloque le planning meme vers des buts en zone libre. Voir
      section 7. Decision a prendre : retoucher les params d'inflation ou
      refaire une session de mapping plus complete.

## 1. Build

```
colcon build --symlink-install
source install/setup.bash
```
Verifier qu'il ne manque pas `nav2_bringup`, `nav2_map_server`, `nav2_amcl`,
`nav2_controller`, `nav2_planner`, `nav2_behaviors`, `nav2_bt_navigator`,
`nav2_waypoint_follower`, `nav2_velocity_smoother`, `nav2_lifecycle_manager`,
`slam_toolbox`, `pointcloud_to_laserscan` sur la machine qui va reellement
tourner (onboard du robot, pas ce laptop de dev).

## 2. Sanity check moteur (adapter + teleop maintenant lies)

```
ros2 launch quadruped_bringup mapping.launch.py robot:=b2
ros2 run quadruped_bringup teleop
```
- Verifier que `robot_adapter` demarre bien tout seul avec le launch (log
  "SportClient B2 initialise").
- Verifier : le robot avance/recule/tourne correctement, le watchdog coupe
  bien le mouvement si plus rien n'est publie 500ms.

## 3. Mapping (deja valide, a rejouer pour confirmer le fix + la nouvelle structure)

- Verifier que le TF `map -> odom -> robot_center -> rslidar` est complet
  (`ros2 run tf2_tools view_frames`).
- Verifier que la carte se construit/se recale en bougeant peu (le fix
  2cm doit se voir : plus besoin de faire un grand trajet pour que
  slam_toolbox recale).
- Sauver une nouvelle carte si besoin :
  `ros2 run nav2_map_server map_saver_cli -f src/quadruped_bringup/maps/<nom>`
  puis **`colcon build --symlink-install`** pour qu'elle soit visible du launch nav2.

## 4. Navigation (AMCL + DWB + waypoints) — le nouveau morceau, jamais teste

```
ros2 launch quadruped_nav2 navigation.launch.py robot:=b2
```
Sans `map:=`, prend automatiquement la derniere carte sauvegardee (par date
de modification) dans `maps/`. Verifier dans les logs que c'est bien la bonne
carte qui est chargee avant de continuer.
- [ ] Les lifecycle managers passent bien tous les noeuds en `active`
  (`ros2 lifecycle list /amcl`, etc., ou `ros2 topic echo /amcl/transition_event`).
- [ ] AMCL converge : donner une pose initiale dans RViz (`2D Pose Estimate`),
  verifier que le nuage de particules se resserre en bougeant un peu.
- [ ] Costmap locale : verifier dans RViz que les obstacles reels (mur,
  personne) apparaissent bien sur `/local_costmap/costmap`.
- [ ] Envoyer un `Nav2 Goal` simple dans RViz, verifier que le robot
  planifie et suit le chemin.
- [ ] Mettre un obstacle sur le trajet : verifier que DWB devie/replanifie
  sans foncer dedans.
- [ ] Poser 2-3 waypoints via le plugin RViz *Nav2 Waypoint/Goal* et
  lancer la tournee, verifier l'enchainement.

## 5. Points a mesurer/ajuster une fois sur le vrai robot

- `robot_radius` (0.45 par defaut dans `nav2_params_b2.yaml`) — mesurer
  l'encombrement reel pattes ecartees.
- Limites de vitesse DWB (`max_vel_x/y/theta`, `acc_lim_*`) — comparer
  au comportement reel observe a l'etape 2.
- Offset physique reel du LiDAR pour la TF statique (point 0).

## 6. Debug session 2026-07-13 — navigation ne demarre pas malgre tous les nodes actifs

### Symptome
Tous les nodes attendus tournent (`ros2 node list` complet, `/dog_odom` a
500Hz), mais `view_frames` ne montre que la TF statique `robot_center ->
rslidar`. Aucune TF dynamique. Navigation bloquee silencieusement, aucune
erreur explicite nulle part.

### Piege rencontre en diagnostiquant : mismatch RMW entre le shell et le robot
`ros2 param get`, `ros2 lifecycle get /amcl`, etc. restaient bloques
indefiniment (timeout), ce qui ressemblait a un lifecycle manager bloque.
En verite : **tous les nodes du stack tournent avec
`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`** (verifie via
`/proc/<pid>/environ` sur amcl, controller_server, odom_to_tf,
pointcloud_to_laserscan, lifecycle managers...), alors qu'un shell qui ne
source pas cette variable retombe sur le defaut `rmw_fastrtps_cpp`. Les
topics simples passent quand meme (RTPS de base interoperable), mais les
appels de service/lifecycle entre deux implementations DDS differentes ne
repondent jamais.
**Le commentaire dans `profiles/b2.yaml` qui dit d'exporter
`RMW_IMPLEMENTATION=rmw_fastrtps_cpp` est FAUX/perime** — le robot tourne
en cyclonedds. A corriger (voir TODO code). En attendant : toujours faire
`export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` (+ `ROS_DOMAIN_ID=0`) dans
tout shell de diagnostic ou avant de lancer RViz depuis un autre PC, sinon
les symptomes de service/lifecycle "muet" sont trompeurs.

### Vraie cause racine trouvee : `/scan` n'est jamais publie
Une fois le RMW aligne, confirme proprement :
- `/rslidar_points` publie bien a 10Hz (rslidar_sdk fonctionne).
- `/scan` ne publie STRICTEMENT rien (`ros2 topic hz /scan` reste muet).
- Le node `pointcloud_to_laserscan` est bien souscrit a `/rslidar_points`
  (confirme par `ros2 node info`), ses parametres sont sains
  (`target_frame: rslidar` = meme frame que le nuage source, donc pas de
  lookup TF distant necessaire).
- Dans le log de lancement (`~/.ros/log/<derniere session>/launch.log`),
  **156 occurrences** d'une erreur DDS repetee, uniquement sur
  `pointcloud_to_laserscan_node` :
  ```
  rcutils_set_error_state() ... 'invalid data size' / 'string data is not
  null-terminated', at .../rmw_cyclonedds_cpp/src/serdata.cpp:384
  ```
  Cette erreur vient du **build custom de `rmw_cyclonedds_cpp` dans
  `~/slam_config/cyclonedds_go2_B2_ws`** (pas un depot git, pas de version
  tracable), utilise via `LD_LIBRARY_PATH`. Elle correspond typiquement a
  un bug de deserialisation des champs `string` imbriques — ici tres
  probablement le champ `name` de chaque `sensor_msgs/PointField` a
  l'interieur du `PointCloud2`. Aucun autre node du graph (qui ne recoit
  pas de `PointCloud2`) ne montre cette erreur.
- Conclusion : `pointcloud_to_laserscan` recoit bien les messages au
  niveau DDS mais echoue a les deserialiser correctement a cause de ce
  bug dans le build custom du RMW -> le callback ne produit jamais de
  `/scan` valide -> `odom_to_tf.publish_tf()` (appelee uniquement depuis
  `scan_cb()`, voir couplage ci-dessous) n'est jamais declenchee -> aucune
  TF dynamique -> AMCL ne recoit jamais rien -> navigation bloquee, sans
  erreur visible cote nav2/amcl puisque c'est tout en amont, au niveau
  DDS.

### A faire ensuite (pas encore fait, discussion necessaire avant de coder)
- [ ] Isoler le bug de deserialisation : tester si `pointcloud_to_laserscan`
  lance avec le `rmw_cyclonedds_cpp` standard (paquet apt
  `ros-humble-rmw-cyclonedds-cpp`) au lieu du build custom
  `cyclonedds_go2_B2_ws` reproduit le meme souci ou pas. Si le paquet
  standard fonctionne, ca confirme un bug/patch specifique au build
  custom plutot qu'un bug upstream cyclonedds. Attention : le build
  custom sert peut-etre a parler au SDK bas niveau Unitree (motion
  control) — bien verifier ce qui d'autre en depend avant d'y toucher.
- [ ] Une fois confirme, soit patcher/mettre a jour le build custom, soit
  isoler `pointcloud_to_laserscan` dans un processus qui utilise un RMW
  different (si les deux RMW peuvent cohabiter sur le meme domaine sans
  casser le reste — a valider, pas garanti).
- [ ] Corriger le commentaire perime dans `profiles/b2.yaml`
  (`rmw_fastrtps_cpp` -> `rmw_cyclonedds_cpp`).

### Suite et fix appliques le 2026-07-13 (apres la session ci-dessus)

**1. Fix `pointcloud_to_laserscan` — contournement valide.**
Dans `quadruped_bringup/launch/sensors.launch.py`, le node `pointcloud_to_laserscan`
recoit maintenant un `additional_env` qui retire `~/slam_config/cyclonedds_go2_B2_ws`
de son `LD_LIBRARY_PATH`/`AMENT_PREFIX_PATH`, pour qu'il resolve `rmw_cyclonedds_cpp`
via le paquet standard apt (`ros-humble-rmw-cyclonedds-cpp`, cyclonedds 0.10.4) au
lieu du build custom bugue. Le reste du stack (`static_tf`, `odom_to_tf`, tout nav2)
garde le build custom — pas touche au SDK bas niveau Unitree.
Valide en conditions reelles : `/scan` publie a ~10Hz, plus aucune erreur
`invalid data size`/`string data is not null-terminated` sur ce node, TF complete
`map -> odom -> robot_center -> rslidar` confirmee via `view_frames` (rate ~10.2Hz,
`odom -> robot_center` avec des valeurs saines, ex. z ~0.486m = hauteur debout B2).
Le bug lui-meme (deserialisation des `PointField[]` dans le build custom) reste
non corrige a la racine — voir "A faire ensuite" plus haut si on veut vraiment
regler ca un jour (mise a jour du submodule cyclonedds custom vers 0.10.4+).

**2. Nouveau bug trouve en testant : crash `robot_adapter` avec RMW cyclonedds.**
En forcant `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` sur tout le launch (necessaire
pour le reste du stack, voir fix OOM plus haut dans ce fichier / memoire projet),
`robot_adapter` plantait au demarrage :
```
terminate called after throwing an instance of 'unitree::common::DdsException'
what(): Catch dds::core exception. Class:::dds::core::PreconditionNotMetError,
Message:Error Precondition Not Met - Failed to create domain explicitly.
Context: org::eclipse::cyclonedds::domain::DomainWrap::DomainWrap
```
Cause identifiee en lisant `quadruped_adapter/src/robot_adapter.cpp` : `main()`
appelle `rclcpp::init()` (ligne 111) qui cree un domain participant cyclonedds
IMPLICITE (domaine 0) des que `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` ; puis le
constructeur de `RobotAdapter` appelle `ChannelFactory::Instance()->Init(0, iface)`
(ligne 36) qui cree un domain participant cyclonedds EXPLICITE, meme domaine, meme
processus -> CycloneDDS refuse (un domaine ne peut pas avoir un participant
explicite si un implicite existe deja dans le meme processus). Defaut structurel
preexistant dans `robot_adapter.cpp`, pas cause par le fix ci-dessus — se declenche
des que quelqu'un lance ce node avec cyclonedds cote ROS (ce qui n'arrivait jamais
avant car `robot_adapter` etait lance a la main via `ros2 run`, sans exporter
`RMW_IMPLEMENTATION`, donc ROS restait par defaut sur fastrtps -> pas de conflit).

**Fix applique** dans `quadruped_bringup/launch/actuation.launch.py` : le node
`robot_adapter` recoit `additional_env={'RMW_IMPLEMENTATION': 'rmw_fastrtps_cpp'}`
pour rester sur fastrtps cote ROS pendant que le reste du stack garde cyclonedds —
pas touche a `robot_adapter.cpp` ni au SDK. Valide : `SportClient B2 initialise`,
`ros2 topic info /cmd_vel -v` confirme `robot_adapter` bien abonne malgre le RMW
different, et `robot_adapter` a effectivement recu/execute des commandes de
mouvement reelles (`Move -> vx=-0.05 ...`, `vyaw=0.80`) pendant les comportements
de recuperation nav2 (backup/spin) lors des tests de navigation ci-dessous.

**3. Test navigation reelle (2D Pose Estimate + 2D Goal Pose depuis RViz) : 3/3 buts echoues.**
Chaine complete confirmee fonctionnelle de bout en bout (RViz -> nav2 -> `/cmd_vel`
-> `robot_adapter` -> SDK -> mouvement reel), mais `planner_server` n'a jamais
reussi a calculer un chemin (`GridBased: failed to create plan with tolerance 0.50`)
vers aucun des 3 buts testes, meme apres clear costmap + comportements de
recuperation (backup/spin/wait) executes en vrai sur le robot.
Diagnostic fait en lisant directement `b2_map_2026-07-10.pgm` (pas juste les logs) :
- Carte tres peu exploree : ~84% des pixels en "unknown" (205), seulement ~43m²
  de zone "libre" (254) sur les ~300m² de la carte (422x284 px @ 0.05m/px).
- Les 3 points de but testes tombent bien en zone "libre" sur la carte brute, et
  une verification de connectivite (BFS en evitant seulement les pixels
  strictement occupes) confirme qu'un chemin existe geometriquement entre le
  robot et chaque but — donc PAS un vrai mur qui bloque.
- Hypothese la plus probable : `robot_radius: 0.45` + `inflation_radius: 0.55`
  (`nav2_params_b2.yaml`) demandent ~1m de degagement par rapport a tout obstacle
  mappe ; dans une zone aussi peu et etroitement exploree (le robot a demarre tres
  pres d'un mur mappe — sa position de depart initiale tombait meme sur un pixel
  occupe de la carte), le costmap gonfle avale probablement tout le corridor
  navigable malgre une carte brute "libre".

**A faire ensuite (pas fait, discussion en cours) :**
- [ ] Decider : (A) retoucher `robot_radius`/`inflation_radius` a la baisse pour
      tester si ca debloque le planning dans cette zone serree (reduit la marge
      de securite), ou (B) refaire une session de mapping plus complete/large
      pour avoir une vraie carte exploitable plutot que de naviguer sur une
      carte a 84% inconnue.
- [ ] Comprendre pourquoi la position de depart initiale de `robot_adapter`
      tombait sur un pixel occupe de la carte (alignement TF/carte a verifier ?).

### Point de vigilance permanent : couplage cache TF/scan dans `odom_to_tf.py`
Dans `src/quadruped_bringup/quadruped_bringup/odom_to_tf.py`, `publish_tf()`
(qui publie `odom -> robot_center`) n'est appelee QUE depuis `scan_cb()`,
donc uniquement quand un message arrive sur `/scan` — pas sur un timer
independant declenche par `/dog_odom`. C'est fait expres pour synchroniser
les timestamps TF/scan, mais consequence directe : **toute panne silencieuse
n'importe ou dans la chaine LiDAR (`rslidar_sdk` -> `/rslidar_points` ->
`pointcloud_to_laserscan` -> `/scan`) coupe integralement la publication de
TF, meme si l'odometrie (`/dog_odom`) fonctionne parfaitement** — sans
aucune erreur explicite cote nav2/amcl/lifecycle. C'est exactement ce qui
s'est passe ici. A garder en tete pour tout futur debug de navigation :
si `view_frames` ne montre pas de TF dynamique, verifier `/scan` et toute
sa chaine AVANT de suspecter `odom_to_tf.py`, AMCL ou les lifecycle
managers. Ne pas decoupler ce couplage (ex: publier la TF sur un timer
independant de `/scan`) sans validation explicite au prealable — la
synchro des timestamps est peut-etre voulue et importante ailleurs dans le
stack (costmap, filtres, etc.).
