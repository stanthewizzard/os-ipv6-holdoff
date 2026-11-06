"""Pure holdoff policy; all elapsed times use a monotonic clock."""
def transition(state, *, now, master, preferred, delay, enabled, prefix):
    since = state.get('since')
    if not enabled or not master:
        return {'since': None, 'phase': 'disabled' if not enabled else 'backup', 'remaining': 0, 'advertise': False}
    if since is None or now < since:
        since = now
    remaining = 0 if preferred else max(0, delay - int(now - since))
    return {'since': since, 'phase': 'waiting' if remaining else ('active' if prefix else 'no_delegation'),
            'remaining': remaining, 'advertise': bool(prefix) and remaining == 0}
