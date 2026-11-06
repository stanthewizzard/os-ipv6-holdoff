import importlib.util
from pathlib import Path
import unittest
import ast
import re
from types import SimpleNamespace

path = Path(__file__).parent/'src/usr/local/opnsense/scripts/ipv6holdoff/policy.py'
spec=importlib.util.spec_from_file_location('policy',path)
policy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

class PolicyTests(unittest.TestCase):
    def tick(self, state=None, **kwargs):
        args=dict(now=100,master=True,preferred=False,delay=600,enabled=True,prefix='2001:db8:1::/64')
        args.update(kwargs)
        return policy.transition(state or {}, **args)

    def test_secondary_waits_full_ten_minutes(self):
        state=self.tick()
        self.assertFalse(state['advertise'])
        self.assertEqual(self.tick(state,now=699)['remaining'],1)
        self.assertTrue(self.tick(state,now=700)['advertise'])

    def test_preferred_node_does_not_wait(self):
        self.assertTrue(self.tick(preferred=True)['advertise'])

    def test_primary_return_cancels_pending_activation(self):
        state=self.tick()
        state=self.tick(state,now=500,master=False)
        self.assertFalse(self.tick(state,now=900)['advertise'])
        self.assertEqual(self.tick(state,now=900)['remaining'],600)

    def test_restart_restarts_safe_delay(self):
        self.assertEqual(self.tick(now=1000)['remaining'],600)

    def test_no_delegation_never_advertises(self):
        state=self.tick()
        self.assertFalse(self.tick(state,now=1000,prefix=None)['advertise'])

    def test_disable_withdraws_and_resets_timer(self):
        state=self.tick(preferred=True)
        state=self.tick(state,enabled=False)
        self.assertFalse(state['advertise'])
        self.assertIsNone(state['since'])

class WithdrawalTests(unittest.TestCase):
    def load(self, returncode=0, current=''):
        tree=ast.parse(path.with_name('worker.py').read_text())
        fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='withdraw')
        events=[]
        def remove(*args,**kwargs):
            events.append('remove_address')
            return SimpleNamespace(returncode=returncode)
        environment={'subprocess':SimpleNamespace(run=remove),'re':re,
                     'run':lambda args: current,'render':lambda *args: events.append('render_ula')}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<withdrawal>','exec'),environment)
        return environment['withdraw'],events

    def test_remove_address_before_native_generation(self):
        withdraw,events=self.load()
        withdraw(('vtnet0','2001:4860::1234'),'lan')
        self.assertEqual(events,['remove_address','render_ula'])

    def test_retry_with_already_absent_address_still_withdraws_prefix(self):
        withdraw,events=self.load(returncode=1)
        withdraw(('vtnet0','2001:4860::1234'),'lan')
        self.assertEqual(events,['remove_address','render_ula'])

    def test_failed_removal_does_not_claim_success(self):
        withdraw,events=self.load(returncode=1,current='inet6 2001:4860::1234 prefixlen 64')
        with self.assertRaises(RuntimeError): withdraw(('vtnet0','2001:4860::1234'),'lan')
        self.assertEqual(events,['remove_address'])

if __name__=='__main__': unittest.main()
