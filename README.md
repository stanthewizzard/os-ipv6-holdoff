# IPv6 Public Holdoff for OPNsense

Je propose ce plugin pour conserver une reprise CARP/IPv4 immédiate tout en temporisant l'annonce du préfixe IPv6 public sur le pare-feu secondaire.

Le LAN conserve ses ULA et le RADVD natif. Le nœud préféré peut annoncer sa délégation publique lorsqu'il est MASTER ; le secondaire attend 600 secondes continues en MASTER. Le retour en BACKUP annule l'attente. Le délai repart après redémarrage du service. Les connexions utilisant un ancien préfixe peuvent être interrompues lors d'une bascule.

## Distribution

Les sources sont dans `src/`. Les catalogues et paquets signés destinés à `pkg` sont dans `repository/26.7/FreeBSD-15-amd64/`. La clé publique de vérification est `repository-public.pem`. La clé privée reste hors du dépôt.

Git conserve les sources ; OPNsense Firmware installe les paquets avec `pkg`. Le dépôt GitHub public héberge directement les catalogues et paquets signés en HTTPS. Aucun PAT, cache de synchronisation, serveur supplémentaire ou `git pull` dans les répertoires système n'est nécessaire.

## État et compatibilité

Version 0.1.8, pour OPNsense 26.7.8_2 / FreeBSD:15:amd64. Neuf tests ciblés couvrent le délai, son annulation et le retrait des annonces. Depuis 0.1.7, la configuration amont est conservée pendant une mise à jour et restaurée lors d'une vraie désinstallation. La version 0.1.8 référence le dépôt GitHub du projet dans les métadonnées du paquet ; elle ne change pas le fonctionnement des annonces IPv6.

Le redémarrage du service, le retrait/reprise du préfixe et les accès IPv4/IPv6 ont été testés. Aucun reboot complet ni bascule réelle prolongée de dix minutes n'a été validé. Chaque nouvelle version majeure d'OPNsense nécessite une nouvelle validation.

Le service ne remplace pas une délégation IPv6 fonctionnelle. La Livebox ou le routeur amont doit router la délégation vers le pare-feu concerné. Les règles de routage et de filtrage doivent être adaptées à l'installation.
