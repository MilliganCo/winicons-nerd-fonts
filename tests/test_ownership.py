import ast
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.icons = self.base / 'icons'
        self.icons.mkdir()
        self.inside = self.icons / 'owned.ico'
        self.inside.touch()
        self.outside = self.base / 'outside'
        self.outside.mkdir()
        (self.outside / 'foreign.ico').touch()
        source = Path(__file__).parents[1] / 'nficons.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'ours', 'icon_line'}]
        self.assertEqual({n.name for n in nodes}, {'ours', 'icon_line'})
        namespace = {'os': os, 'ICONS': str(self.icons)}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
        self.ours = namespace['ours']
        self.icon_line = namespace['icon_line']

    def test_plain_indexed_and_quoted_resource_values(self):
        for value in (str(self.inside), f'{self.inside},0', f'"{self.inside}",-2'):
            _, parsed = self.icon_line(['[.ShellClassInfo]', 'IconResource=' + value])
            self.assertTrue(self.ours(parsed))

    def test_sibling_prefix_and_parent_escape_are_not_owned(self):
        self.assertFalse(self.ours(str(self.base / 'icons-other' / 'foreign.ico') + ',0'))
        self.assertFalse(self.ours(str(self.icons / '..' / 'outside' / 'foreign.ico') + ',0'))

    def test_internal_parent_segments_and_windows_case(self):
        (self.icons / 'sub').mkdir()
        self.assertTrue(self.ours(str(self.icons / 'sub' / '..' / 'owned.ico')))
        self.assertTrue(self.ours(str(self.inside).upper() + ',0'))

    def test_relative_and_environment_descriptors_are_untouched(self):
        for value in (None, '', r'.\icons\owned.ico,0', r'C:owned.ico,0', r'%TEMP%\icons\owned.ico,0'):
            self.assertFalse(self.ours(value))

    def test_other_drive_does_not_trigger_a_path_lookup(self):
        other = 'Y:' if self.icons.drive.upper() == 'Z:' else 'Z:'
        with patch.object(os.path, 'realpath', side_effect=AssertionError('unexpected path lookup')):
            self.assertFalse(self.ours(other + r'\not-real\owned.ico,0'))

    def test_symlink_escape_and_owned_alias(self):
        escape = self.icons / 'escape'
        alias = self.base / 'alias'
        try:
            escape.symlink_to(self.outside, target_is_directory=True)
            alias.symlink_to(self.icons, target_is_directory=True)
        except OSError as exc:
            self.skipTest('Temporary symlink unavailable: ' + str(exc))
        self.assertFalse(self.ours(str(escape / 'foreign.ico') + ',0'))
        self.assertTrue(self.ours(str(alias / 'owned.ico') + ',0'))


if __name__ == '__main__':
    unittest.main()
