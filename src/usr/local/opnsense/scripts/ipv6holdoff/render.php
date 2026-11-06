<?php
/* Add a runtime-only VIP to the native generator; never persist it. */
require_once('script/load_phalcon.php');
require_once('config.inc');
require_once('util.inc');
require_once('interfaces.inc');
require_once('plugins.inc');
require_once('plugins.inc.d/radvd.inc');
$request = json_decode(stream_get_contents(STDIN), true, 8, JSON_THROW_ON_ERROR);
$interface = $request['interface'] ?? '';
$address = $request['address'] ?? null;
if (!isset($config['interfaces'][$interface])) {
    throw new RuntimeException('Unknown downstream interface');
}
if ($address !== null) {
    if (!filter_var($address, FILTER_VALIDATE_IP, FILTER_FLAG_IPV6) || !preg_match('/^[23]/', $address)) {
        throw new RuntimeException('Global IPv6 address required');
    }
    $config['virtualip']['vip'][] = ['interface' => $interface, 'mode' => 'ipalias',
        'subnet' => $address, 'subnet_bits' => '64', 'descr' => 'IPv6 holdoff runtime prefix'];
}
if (in_array('--preview', $argv, true)) {
    /* Execute the installed generator up to its first write, without changing it. */
    $reflection = new ReflectionFunction('radvd_configure_do');
    $lines = file($reflection->getFileName());
    $body = implode('', array_slice($lines, $reflection->getStartLine()-1,
        $reflection->getEndLine()-$reflection->getStartLine()+1));
    $body = str_replace('function radvd_configure_do(', 'function holdoff_preview(', $body);
    $marker = '    file_safe($radvd_conf_file, $radvdconf);';
    if (substr_count($body, $marker) !== 1) throw new RuntimeException('Unsupported RADVD generator');
    $body = substr($body, 0, strpos($body, $marker)) . "    return " . '$radvdconf;' . "\n}";
    eval($body);
    echo holdoff_preview();
} else {
    radvd_configure_do();
}
