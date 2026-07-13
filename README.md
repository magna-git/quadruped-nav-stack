# quadruped-nav-stack

Stack de navigation ROS 2 (Jazzy) pensé pour etre **reutilisable sur plusieurs
robots**, pas seulement le B2-W. L'objectif n'est pas "un stack pour le B2",
mais un socle generique (perception, SLAM, localisation, evitement
d'obstacles, waypoints) qu'on porte d'un robot a l'autre en ne changeant que
la couche specifique au materiel — aujourd'hui le B2-W d'Unitree, demain par
exemple la D1 max d'AgiBot.

## Principe : ce qui est generique vs ce qui est specifique au robot

| Generique (reutilise tel quel) | Specifique au robot (a rejouer par robot) |
|---|---|
| `quadruped_bringup` (perception, TF, mapping) | `profiles/<robot>.yaml` (topics, frames, limites) |
| `quadruped_nav2` (AMCL, DWB, costmaps, waypoints) | `config/slam_config_<robot>.yaml` |
| logique de `odom_to_tf`, `sensors.launch.py`, `navigation.launch.py` | `config/nav2_params_<robot>.yaml` |
| | `quadruped_adapter` (pont `/cmd_vel` -> SDK constructeur) |

Le seul morceau **impossible a reutiliser tel quel** est `quadruped_adapter` :
il appelle directement le SDK Unitree B2. Porter le stack sur un robot d'un
autre constructeur (AgiBot D1max, etc.) veut dire ecrire un adapter
equivalent qui expose le meme contrat (`/cmd_vel` en entree, limites
vx/vy/vyaw appliquees, watchdog) mais parle au SDK du nouveau robot. Tout le
reste (perception, SLAM, nav2) ne bouge pas.

## Structure du workspace

```
src/
  quadruped_adapter/       Pont cmd_vel -> SDK Unitree (C++), watchdog inclus
                           -> SPECIFIQUE B2, a reimplementer pour un autre robot
  quadruped_bringup/
    profiles/b2.yaml       Profil robot : topics, frames, limites de vitesse
                           -> charge reellement par odom_to_tf, pointcloud_to_laserscan
                              et robot_adapter (pas juste documentaire)
    launch/sensors.launch.py     TF lidar, odom_to_tf, pointcloud_to_laserscan
    launch/actuation.launch.py   Lance quadruped_adapter (parametre par profiles/<robot>.yaml)
    launch/mapping.launch.py     sensors + actuation + slam_toolbox (mode mapping)
    config/slam_config_b2.yaml   Parametres slam_toolbox specifiques B2
    maps/                        Cartes sauvegardees (.pgm/.yaml)
  quadruped_nav2/
    launch/navigation.launch.py  sensors + actuation + AMCL + DWB + waypoints
    config/nav2_params_b2.yaml   Tous les parametres nav2, specifiques B2, commentes
profiles/                  (n'existe plus a la racine, deplace dans quadruped_bringup)
```

## Prerequis : RMW CycloneDDS

**Obligatoire sur le robot ET sur toute machine distante (RViz, PC de dev)**
avant de builder/lancer quoi que ce soit :

```
source scripts/setup_env.sh
```

Ce script bascule le RMW de Fast-DDS (defaut ROS2) vers CycloneDDS. Raison :
Fast-DDS + son transport shared-memory explose en RAM avec les gros messages
nav2 (carte, costmaps) et peut declencher un OOM qui tue tous les noeuds
d'un coup en quelques secondes (voir section "Erreurs deja rencontrees").
`rmw_cyclonedds_cpp` est declare en `exec_depend` dans les `package.xml`
(`quadruped_bringup`, `quadruped_nav2`) pour rappeler qu'il est requis.

Toutes les machines qui doivent se decouvrir (meme `ROS_DOMAIN_ID`, ex:
robot + PC RViz) doivent utiliser le meme RMW et la meme interface reseau.
`scripts/cyclonedds.xml` cible `eth0` par defaut : ajuster si l'interface
differe (`ip -o link show` pour lister les interfaces disponibles).

## Build

```
colcon build --symlink-install
source install/setup.bash
```

## Quel launch lancer ?

**Une carte existe deja pour ce robot/cet environnement ?** Verifie
`src/quadruped_bringup/maps/*.yaml` (ou `share/quadruped_bringup/maps/` dans
`install/` si deja buildee) : s'il y a un fichier recent, saute directement a
"Navigation" ci-dessous — `navigation.launch.py` charge tout seul la carte la
plus recente, pas besoin de refaire un mapping.

**Pas de carte (nouveau robot, nouvel espace)** : fais d'abord "Mapping" pour
en creer une, *puis* "Navigation".

| Tu veux... | Lance... | Inclut |
|---|---|---|
| Cartographier un nouvel espace / carte absente ou perimee | `mapping.launch.py` | perception + actuation + slam_toolbox |
| Naviguer avec une carte deja sauvegardee | `navigation.launch.py` | perception + actuation + AMCL + DWB + waypoints |
| Juste piloter a la manette/teleop, sans SLAM ni nav | `actuation.launch.py` + `teleop.py` | uniquement le pont `/cmd_vel` -> SDK |

## Mapping

```
ros2 launch quadruped_bringup mapping.launch.py robot:=b2
```

Lance perception + actuation (teleop possible pendant le mapping) +
slam_toolbox. Sauver la carte une fois satisfaisante :

```
ros2 run nav2_map_server map_saver_cli -f src/quadruped_bringup/maps/<nom_carte>
```

`map_saver_cli` sauve directement le `.pgm`/`.yaml` en ecoutant le topic
`/map` publie par slam_toolbox — pas besoin de lancer `map_server` toi-meme,
c'est un noeud different (celui qui *sert* une carte a AMCL pendant la
navigation, deja inclus dans `navigation.launch.py`).

Important : les cartes sont installees dans le package (`share/quadruped_bringup/maps`).
Apres un nouveau `map_saver_cli` dans `src/quadruped_bringup/maps/`, refaire
`colcon build --symlink-install` (rapide, package Python) pour que la nouvelle
carte soit visible au prochain lancement de la navigation.

## Navigation (localisation + evitement d'obstacles + waypoints)

```
ros2 launch quadruped_nav2 navigation.launch.py robot:=b2
```

`map:=` est optionnel : si omis, le launch prend automatiquement la carte la
plus recente (par date de modification) dans `maps/`. Passe `map:=<chemin>.yaml`
explicitement pour forcer une carte precise.

- **Localisation** : AMCL sur la carte statique.
- **Evitement d'obstacles** : costmap locale alimentee par `/scan_synced`, controller DWB.
- **Waypoints** : dans RViz, plugin *Nav2 Waypoint/Goal*, poser plusieurs points puis
  lancer la mission. Alternative scriptee possible via `nav2_simple_commander`
  (`follow_waypoints`) si besoin d'automatiser une tournee.

## Porter le stack sur un nouveau robot (ex: AgiBot D1max)

1. `cp src/quadruped_bringup/profiles/b2.yaml src/quadruped_bringup/profiles/d1max.yaml`
   et ajuster topics/frames/limites de vitesse reelles du nouveau robot.
2. Copier `config/slam_config_b2.yaml` -> `slam_config_d1max.yaml` et
   `quadruped_nav2/config/nav2_params_b2.yaml` -> `nav2_params_d1max.yaml`,
   en gardant les memes noms de frames que dans le profil (ces deux fichiers
   restent autonomes, ils ne lisent pas le profil directement).
3. Ecrire un nouveau package adapter (ex: `d1max_adapter`) qui souscrit
   `/cmd_vel`, clamp aux limites du profil, et pilote le SDK du robot —
   meme contrat que `quadruped_adapter`.
4. Lancer avec `robot:=d1max`.

## Erreurs deja rencontrees / points a double-checker

Deux categories volontairement distinguees : ce qu'on a **deja casse et
corrige** (pour ne pas retomber dedans sur un autre robot), et ce qui est
**encore une valeur par defaut non verifiee** (a mesurer avant un vrai
deploiement).

**Deja corrige, a surveiller sur un nouveau robot :**
- `minimum_travel_distance`/`minimum_travel_heading` (slam_toolbox) et
  `update_min_d`/`update_min_a` (AMCL) : les valeurs par defaut habituelles
  (~0.2 = 20cm) empechaient toute mise a jour tant que le robot n'avait pas
  parcouru une grande distance -> carte/localisation qui ne suivait pas.
  Corrige a 0.02 (2cm) pour le B2-W. A revalider sur tout nouveau robot avant
  de supposer que les defauts "standards" conviennent.
- `teleop.py` publiait par defaut sur un topic (`/b2_unit_001/hardware/cmd_vel`)
  different de celui ecoute par `quadruped_adapter` (`/cmd_vel`) -> la teleop
  ne faisait rien sans `--topic` explicite. Corrige (meme defaut partout).
- `quadruped_adapter` n'etait lance dans aucun launch file -> corrige via
  `actuation.launch.py`, inclus par mapping et navigation.
- `profiles/b2.yaml` n'etait charge par aucun noeud (verifie par grep) :
  simple doc, jamais lu -> corrige, c'est maintenant un vrai fichier de
  parametres ROS2 (`/**: ros__parameters:`) charge au lancement.
- **`pointcloud_to_laserscan` ne publiait jamais sur `/scan`** (2026-07-13) :
  bug de deserialisation des `PointField[]` dans le build custom
  `rmw_cyclonedds_cpp` (`~/slam_config/cyclonedds_go2_B2_ws`, pas versionne) ->
  aucune TF dynamique publiee (couplage avec `scan_cb()` dans `odom_to_tf.py`),
  navigation bloquee silencieusement, sans erreur cote nav2/amcl. Contourne
  dans `sensors.launch.py` : ce node force le paquet standard apt
  (`ros-humble-rmw-cyclonedds-cpp`) via `additional_env`, en retirant
  `cyclonedds_go2_B2_ws` de son `LD_LIBRARY_PATH`/`AMENT_PREFIX_PATH` ; le
  reste du stack garde le build custom. A surveiller sur tout nouveau robot
  qui reutiliserait ce meme build custom cyclonedds. Detail complet :
  `TESTS_DEMAIN.md` section 6-7.
- **`robot_adapter` plante au demarrage avec `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`**
  (2026-07-13) : le SDK Unitree (`ChannelFactory::Instance()->Init()`) cree son
  propre domain participant CycloneDDS explicite, qui entre en conflit avec
  celui cree implicitement par `rclcpp::init()` sur le meme domaine (0) dans le
  meme processus (`PreconditionNotMetError - Failed to create domain
  explicitly`). Invisible tant qu'on lance `robot_adapter` a la main sans
  exporter `RMW_IMPLEMENTATION` (fastrtps par defaut -> pas de conflit).
  Contourne dans `actuation.launch.py` : ce node force
  `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` via `additional_env` (les topics
  simples comme `/cmd_vel` restent interoperables entre RMW differents, teste
  et confirme). A surveiller sur tout node qui melange rclcpp et un SDK bas
  niveau utilisant directement CycloneDDS. Detail complet : `TESTS_DEMAIN.md`
  section 7.
- **OOM au lancement de `navigation.launch.py`** (2026-07-10) : tous les
  noeuds nav2 tues d'un coup par le kernel (`Out of memory: Killed process
  ...`, exit code -9 simultane sur amcl/controller_server/planner_server/
  bt_navigator/behavior_server/velocity_smoother/waypoint_follower/
  map_server/...), RSS de chaque noeud grimpant a plusieurs Go en quelques
  secondes. Cause : RMW par defaut (Fast-DDS) + transport shared-memory, qui
  sur-alloue des buffers proportionnels a la taille des messages (carte,
  costmaps) et au nombre de participants DDS decouverts. Corrige en imposant
  `rmw_cyclonedds_cpp` (voir section "Prerequis" plus haut). Si l'OOM revient
  malgre `scripts/setup_env.sh` : verifier qu'il est bien source *avant* le
  `ros2 launch` (dans le meme shell), et que `CYCLONEDDS_URI` pointe vers un
  fichier existant (`echo $CYCLONEDDS_URI`).

**Pas encore verifie, valeurs par defaut a mesurer sur le robot reel :**
- `robot_radius` (0.45 dans `nav2_params_b2.yaml`) : a mesurer pattes
  ecartees, pas encore fait.
- Offset physique reel du LiDAR (TF statique `base -> lidar` dans
  `sensors.launch.py`) : laisse a l'identite (0,0,0,0,0,0), jamais calibre.
- Limites de vitesse DWB (`max_vel_x/y/theta`, `acc_lim_*` dans
  `nav2_params_b2.yaml`) : valeurs de depart raisonnables, pas confrontees au
  comportement reel du B2-W.
- **Couverture de la carte vs `robot_radius`/`inflation_radius`** : sur un
  mapping trop court/etroit (ex. `b2_map_2026-07-10`, ~84% de la carte encore
  "unknown"), le planificateur global peut echouer a trouver un chemin meme
  vers un but en zone nominalement libre, simplement parce que
  `robot_radius` (0.45) + `inflation_radius` (0.55) ne laissent plus de
  corridor navigable dans une zone aussi peu explorée. Sur un nouveau robot :
  faire un mapping large/complet avant de tester la navigation, sinon
  reduire temporairement ces deux valeurs pour diagnostiquer. Detail :
  `TESTS_DEMAIN.md` section 7.

Voir `TESTS_DEMAIN.md` pour le plan de test qui doit lever ces inconnues.
