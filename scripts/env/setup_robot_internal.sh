#!/usr/bin/env bash
# A sourcer avant tout build/launch de ce stack (sur le robot ET sur les PC
# distants qui doivent voir les memes topics, ex: RViz).
#
# Requis : RMW par defaut (Fast-DDS) explose en memoire avec les gros
# messages nav2 (carte, costmaps) et peut declencher un OOM qui tue tous les
# noeuds d'un coup. Voir README, section "Erreurs deja rencontrees".
#
# Meme RMW_IMPLEMENTATION + meme CYCLONEDDS_URI (donc meme interface reseau)
# requis sur toutes les machines du meme ROS_DOMAIN_ID pour qu'elles se
# decouvrent.

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/dds/cyclonedds_robot_internal.xml"
