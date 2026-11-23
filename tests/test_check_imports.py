"""P68: the repository check refuses imports of the project's own modules or names that do not exist."""
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_repository  # noqa: E402


def run(files):
    """Write a small project (path -> source) and return the import errors of its check."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, source in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(source), encoding='utf-8')
        try:
            check_repository.check(root)
        except ValueError as exc:
            return str(exc).replace('\\', '/').splitlines()
        return []


APP = {
    'app/__init__.py': '',
    'app/portal/__init__.py': '',
    'app/portal/combined.py': '''
        import os
        HOSTS = ['a']
        def after_request(): pass
        class Guard: pass
        for _name in ('x',): pass
        try:
            from json import loads as fast_loads
        except ImportError:
            fast_loads = None
        def _later():
            global LATE
            LATE = 1
    ''',
}


class ImportCheck(unittest.TestCase):
    def test_lazy_import_of_a_removed_function_is_refused(self):
        # The P64 defect: an auth hook imported a function that no longer existed, inside the function.
        errors = run({**APP, 'app/portal/mobile.py': '''
            def validate():
                from .combined import before_request
                before_request()
        '''})
        self.assertEqual(errors, ['app/portal/mobile.py:3: imports before_request from app.portal.combined, '
                                  'which does not define it'])

    def test_missing_module_and_absolute_name_are_refused(self):
        errors = run({**APP, 'app/portal/a.py': '''
            import app.portal.gone
            from app.portal.combined import Missing
            from app.nowhere import thing
        '''})
        self.assertEqual(errors, ['app/portal/a.py:2: imports app.portal.gone, which does not exist',
                                  'app/portal/a.py:3: imports Missing from app.portal.combined, which does not define it',
                                  'app/portal/a.py:4: imports app.nowhere, which does not exist'])

    def test_every_kind_of_definition_and_submodule_is_accepted(self):
        self.assertEqual(run({**APP, 'app/portal/ok.py': '''
            from .combined import HOSTS, after_request, Guard, _name, os, fast_loads, LATE
            from . import combined
            from .. import portal
            from app.portal import combined as c
            import app.portal.combined
            import frappe, json
            from frappe.utils import now
        '''}), [])

    def test_optional_and_dynamic_imports_are_left_alone(self):
        self.assertEqual(run({**APP,
            'app/dyn.py': 'globals()["made"] = 1\n',
            'app/lazy.py': 'def __getattr__(name): return name\n',
            'app/use.py': '''
                from .dyn import made
                from .lazy import anything
                try:
                    from .portal.combined import optional_feature
                except ImportError:
                    optional_feature = None
            '''}), [])

    def test_optional_try_does_not_hide_else_and_finally_imports(self):
        errors = run({**APP, 'app/portal/guarded.py': '''
            try:
                from .combined import optional_feature
            except ImportError:
                optional_feature = None
            else:
                from .combined import absent_in_else
            finally:
                from .combined import absent_in_finally
        '''})
        self.assertEqual(errors, [
            'app/portal/guarded.py:7: imports absent_in_else from app.portal.combined, which does not define it',
            'app/portal/guarded.py:9: imports absent_in_finally from app.portal.combined, which does not define it',
        ])

    def test_scripts_import_their_neighbours_but_package_modules_do_not(self):
        script = {'tools/helper.py': 'def ok(): pass\n', 'tools/run.py': 'from helper import ok, missing\n'}
        self.assertEqual(run(script), ['tools/run.py:1: imports missing from helper, which does not define it'])
        # Inside a package a bare name is not a neighbour (Python 3 has no implicit relative import).
        self.assertEqual(run({**APP, 'app/portal/x.py': 'from combined import nothing\n'}), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
