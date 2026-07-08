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

## Build

```
colcon build --symlink-install
source install/setup.bash
```

## Mapping

```
ros2 launch quadruped_bringup mapping.launch.py robot:=b2
```

Lance perception + actuation (teleop possible pendant le mapping) +
slam_toolbox. Sauver la carte une fois satisfaisante :

```
ros2 run nav2_map_server map_saver_cli -f src/quadruped_bringup/maps/<nom_carte>
```

## Navigation (localisation + evitement d'obstacles + waypoints)

```
ros2 launch quadruped_nav2 navigation.launch.py robot:=b2 map:=<chemin_vers_carte>.yaml
```

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

**Pas encore verifie, valeurs par defaut a mesurer sur le robot reel :**
- `robot_radius` (0.45 dans `nav2_params_b2.yaml`) : a mesurer pattes
  ecartees, pas encore fait.
- Offset physique reel du LiDAR (TF statique `base -> lidar` dans
  `sensors.launch.py`) : laisse a l'identite (0,0,0,0,0,0), jamais calibre.
- Limites de vitesse DWB (`max_vel_x/y/theta`, `acc_lim_*` dans
  `nav2_params_b2.yaml`) : valeurs de depart raisonnables, pas confrontees au
  comportement reel du B2-W.

Voir `TESTS_DEMAIN.md` pour le plan de test qui doit lever ces inconnues.
