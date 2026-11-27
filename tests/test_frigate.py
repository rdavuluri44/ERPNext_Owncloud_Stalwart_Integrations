"""P46: the Frigate trial settings keep the login on and never carry camera passwords."""
from pathlib import Path
import json
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'integrations' / 'frigate'
CONFIG = yaml.safe_load((MODULE / 'config.yml').read_text())
README = (MODULE / 'README.md').read_text()
MINIMUM = (0, 18, 3)
CREDENTIAL = re.compile(r'rtsp://([^@\s/]+)@')


def version(text):
    return tuple(int(n) for n in text.split('.'))


class FrigateTrialTests(unittest.TestCase):
    def test_login_stays_on_and_mqtt_off(self):
        self.assertIs(CONFIG['auth']['enabled'], True)
        self.assertTrue(CONFIG['auth'].get('failed_login_rate_limit'))
        self.assertIs(CONFIG['mqtt']['enabled'], False)

    def test_detection_uses_the_bundled_openvino_model(self):
        self.assertEqual(CONFIG['detectors']['ov'], {'type': 'openvino', 'device': 'CPU'})
        self.assertTrue(CONFIG['model']['path'].startswith('/openvino-model/'))

    def test_recording_is_bounded(self):
        record = CONFIG['record']
        self.assertTrue(record['enabled'])
        self.assertTrue(0 < record['continuous']['days'] <= 30)
        for kind in ('alerts', 'detections'):
            self.assertTrue(0 < record[kind]['retain']['days'] <= 30)

    def test_camera_credentials_are_placeholders_only(self):
        texts = [(MODULE / 'config.yml').read_text(), README]
        for text in texts:
            for userinfo in CREDENTIAL.findall(text):
                for part in userinfo.split(':'):
                    self.assertRegex(part, r'^\{FRIGATE_[A-Z0-9_]+\}$', 'a camera login is written in the module')

    def test_pinned_release_is_at_least_the_minimum(self):
        found = re.findall(r'frigate:(\d+\.\d+\.\d+)', README)
        self.assertTrue(found)
        for pin in found:
            self.assertGreaterEqual(version(pin), MINIMUM)
        self.assertRegex(README, r'sha256:[0-9a-f]{64}')

    def test_login_free_port_is_never_published(self):
        self.assertIn('Do not publish port 5000', README)

    def test_upstream_watch_follows_frigate(self):
        catalog = json.loads((ROOT / 'deployment' / 'upstream-watch.json').read_text())
        source = catalog['sources']['frigate']
        self.assertEqual(source['github'], 'blakeblackshear/frigate')
        self.assertTrue(source['host'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
