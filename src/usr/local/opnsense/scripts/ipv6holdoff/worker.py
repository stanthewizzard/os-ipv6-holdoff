#!/usr/local/bin/python3
"""CARP-aware prefix advertisement coordinator. Never writes config.xml."""
import fcntl, ipaddress, json, os, re, signal, subprocess, time
from pathlib import Path
from xml.etree import ElementTree as ET
from policy import transition

BASE = Path('/var/run/ipv6holdoff')
BASE.mkdir(mode=0o700, exist_ok=True)
lock = (BASE / 'lock').open('w')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
stopping = False
def stop(*_):
    global stopping
    stopping = True
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

def run(args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=25).stdout

def settings():
    root = ET.parse('/conf/config.xml').getroot()
    node = root.find('./OPNsense/IPv6Holdoff/general')
    def get(name, default):
        return node.findtext(name, default) if node is not None else default
    upstream = get('upstream', 'wan')
    downstream = get('downstream', 'lan')
    devices = {x.tag: x.findtext('if', '') for x in root.findall('./interfaces/*')}
    return dict(enabled=get('enabled', '0') == '1', observe=get('observe', '1') == '1',
                preferred=get('role', 'secondary') == 'primary', delay=int(get('delay', '600')),
                vhid=int(get('vhid', '30')), hostid=int(get('hostid', 'f202'), 16),
                upstream=upstream, downstream=downstream, wan=devices.get(upstream, ''),
                lan=devices.get(downstream, ''))

def delegated(device):
    # -p reads PD data. Never use -d, which deletes it.
    output = run(['/usr/local/sbin/ifctl', '-i', device, '-6p'])
    nets = set()
    for value in re.findall(r'[0-9a-fA-F:]+/\d+', output):
        net = ipaddress.IPv6Network(value, strict=False)
        if net.prefixlen == 64 and net.subnet_of(ipaddress.IPv6Network('2000::/3')):
            nets.add(str(net))
    if len(nets) > 1:
        raise ValueError('Multiple delegated /64 prefixes; refusing ambiguous selection')
    return next(iter(nets), None)

def status(value):
    temp = BASE / 'status.new'
    temp.write_text(json.dumps(value), encoding='utf-8')
    temp.replace(BASE / 'status.json')

def render(downstream, address):
    payload = json.dumps({'interface': downstream, 'address': address})
    subprocess.run(['/usr/local/bin/php', '/usr/local/opnsense/scripts/ipv6holdoff/render.php'],
                   input=payload, text=True, capture_output=True, check=True, timeout=35)

def withdraw(owned, downstream):
    # Native RADVD can discover a runtime GUA as its primary prefix. Remove it first.
    result = subprocess.run(['/sbin/ifconfig', owned[0], 'inet6', owned[1], 'delete'],
                            capture_output=True, text=True, timeout=25)
    if result.returncode:
        current = run(['/sbin/ifconfig', owned[0]])
        if re.search(r'inet6 ' + re.escape(owned[1]) + r'(?:\s|%)', current):
            raise RuntimeError('Could not remove owned public address')
    render(downstream, None)

state = {}
owned = None
rendered = False
last_config = None
journal = BASE / 'owned.json'
if journal.exists():
    saved = json.loads(journal.read_text())
    if not re.fullmatch(r'[a-zA-Z0-9_.]+', saved[0]) or not ipaddress.IPv6Address(saved[1]).is_global:
        raise ValueError('Invalid ownership journal')
    owned = tuple(saved)
    rendered = True
try:
    while not stopping:
        try:
            cfg = settings()
            if not cfg['wan'] or not cfg['lan'] or cfg['wan'] == cfg['lan']:
                raise ValueError('Separate configured WAN and LAN interfaces are required')
            if cfg != last_config:
                state = {}
                last_config = cfg
            interfaces = run(['/sbin/ifconfig', cfg['lan']])
            matches = re.findall(r'carp: (MASTER|BACKUP|INIT) vhid ' + str(cfg['vhid']) + r'\b', interfaces)
            master = matches == ['MASTER']
            prefix = delegated(cfg['wan']) if cfg['enabled'] else None
            state = transition(state, now=time.monotonic(), master=master,
                               preferred=cfg['preferred'], delay=cfg['delay'],
                               enabled=cfg['enabled'], prefix=prefix)
            desired = str(ipaddress.IPv6Address(int(ipaddress.IPv6Network(prefix).network_address)
                          + cfg['hostid'])) if state['advertise'] and not cfg['observe'] else None
            target = (cfg['lan'], desired) if desired else None
            if owned and owned != target:
                withdraw(owned, cfg['downstream'])
                owned = None
                journal.unlink(missing_ok=True)
                rendered = False
            if target and owned != target:
                # Refuse to take ownership of an existing address.
                if re.search(r'inet6 ' + re.escape(desired) + r'(?:\s|%)', interfaces):
                    raise ValueError('Requested LAN address already exists; choose another host ID')
                run(['/sbin/ifconfig', cfg['lan'], 'inet6', desired + '/64', 'alias'])
                owned = target
                journal.write_text(json.dumps(owned))
                rendered = False
            if target:
                current = run(['/sbin/ifconfig', cfg['lan']])
                line = next((x for x in current.splitlines() if 'inet6 ' + desired + ' ' in x), '')
                if not line or 'duplicated' in line:
                    raise ValueError('Public LAN address failed duplicate address detection')
                if 'tentative' not in line:
                    conf = Path('/var/etc/radvd.conf').read_text()
                    if not rendered or ('prefix ' + prefix + ' {') not in conf:
                        render(cfg['downstream'], desired)
                        rendered = True
            status({**state, 'since': None, 'observe': cfg['observe'], 'prefix': prefix,
                    'address': desired, 'applied': rendered, 'updated': int(time.time()), 'error': None})
        except Exception as exc:
            # Never enable a new prefix after an uncertain observation.
            if owned and last_config:
                try:
                    withdraw(owned, last_config['downstream'])
                    owned = None
                    rendered = False
                    journal.unlink(missing_ok=True)
                except Exception:
                    pass
            status({'phase': 'error', 'error': str(exc), 'applied': rendered, 'updated': int(time.time())})
        for _ in range(5):
            if stopping:
                break
            time.sleep(1)
finally:
    if owned:
        try:
            withdraw(owned, last_config['downstream'])
            journal.unlink(missing_ok=True)
        except Exception:
            pass
