"""Launcher and Home entry points must be discoverable independently."""
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

class AndroidTVManifest(unittest.TestCase):
    def test_launcher_does_not_double_as_home(self):
        root=ET.parse(Path(__file__).resolve().parents[1]/'android-tv/AndroidManifest.xml').getroot()
        ns='{http://schemas.android.com/apk/res/android}'
        app=root.find('application')
        entries={}
        for component in [*app.findall('activity'),*app.findall('activity-alias')]:
            categories=set()
            for intent in component.findall('intent-filter'):
                if any(a.get(ns+'name')=='android.intent.action.MAIN' for a in intent.findall('action')):
                    categories.update(c.get(ns+'name') for c in intent.findall('category'))
            entries[component.get(ns+'name')]=(component,categories)
        launcher=[c for c,cats in entries.values() if 'android.intent.category.LAUNCHER' in cats]
        home=[c for c,cats in entries.values() if 'android.intent.category.HOME' in cats]
        self.assertEqual(len(launcher),1)
        self.assertEqual(len(home),1)
        self.assertIsNot(launcher[0],home[0])
        self.assertIn('android.intent.category.LEANBACK_LAUNCHER',entries[launcher[0].get(ns+'name')][1])
        self.assertEqual(home[0].get(ns+'targetActivity'),launcher[0].get(ns+'name'))
        self.assertEqual(home[0].get(ns+'exported'),'true')
        self.assertIn('android.intent.category.DEFAULT',entries[home[0].get(ns+'name')][1])
