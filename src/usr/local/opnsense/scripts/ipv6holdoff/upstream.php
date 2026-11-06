<?php
// Package upgrades retain the upstream settings; a real uninstall restores them.
if (($argv[1] ?? '') === 'restore' && getenv('PKG_UPGRADE') !== false) exit(0);
require_once('script/load_phalcon.php');
require_once('config.inc');
require_once('util.inc');
require_once('interfaces.inc');
$model = new OPNsense\IPv6Holdoff\IPv6Holdoff();
$interface = (string)$model->general->upstream;
$path = '/usr/local/etc/ipv6holdoff/dhcp6c.conf';
$backup = '/conf/ipv6holdoff-upstream.json';
$action = $argv[1] ?? '';
$keys = ['adv_dhcp6_config_file_override','adv_dhcp6_config_file_override_path'];
if (!isset($config['interfaces'][$interface]) || $config['interfaces'][$interface]['ipaddrv6'] !== 'dhcp6') {
    throw new RuntimeException('A native DHCPv6 upstream is required');
}
if ($action === 'prepare') {
    if (file_exists($backup)) throw new RuntimeException('Upstream already prepared; preserve original backup');
    $original = [];
    foreach ($keys as $key) {
        $original[$key] = $config['interfaces'][$interface][$key] ?? null;
    }
    if (!empty($original[$keys[0]])) throw new RuntimeException('Existing custom DHCPv6 configuration; refusing replacement');
    file_put_contents($backup, json_encode(['interface'=>$interface,'original'=>$original], JSON_THROW_ON_ERROR));
    chmod($backup, 0600);
    $config['interfaces'][$interface][$keys[0]] = '1';
    $config['interfaces'][$interface][$keys[1]] = $path;
    write_config('IPv6 holdoff: request a separate delegation without assigning it to WAN');
} elseif ($action === 'restore') {
    if (!file_exists($backup)) exit(0);
    $saved = json_decode(file_get_contents($backup), true, 8, JSON_THROW_ON_ERROR);
    $interface = $saved['interface'];
    if (($config['interfaces'][$interface][$keys[1]] ?? '') !== $path) {
        throw new RuntimeException('Upstream changed since preparation; manual restoration required');
    }
    foreach ($saved['original'] as $key=>$value) {
        if ($value === null) unset($config['interfaces'][$interface][$key]);
        else $config['interfaces'][$interface][$key] = $value;
    }
    write_config('IPv6 holdoff: restore native upstream configuration');
    unlink($backup);
} else {
    throw new RuntimeException('Use prepare or restore');
}
interface_dhcpv6_prepare($interface, $config['interfaces'][$interface]);
if (mwexecf('/usr/bin/env dhcp6c_config=/var/etc/dhcp6c.conf dhcp6c_flags=-d /usr/local/etc/rc.d/dhcp6c onerestart') !== 0) {
    throw new RuntimeException('DHCPv6 restart failed');
}
echo "Upstream configuration updated\n";
