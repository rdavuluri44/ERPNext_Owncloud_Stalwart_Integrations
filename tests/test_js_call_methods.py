"""P93: every browser call to one of our server functions uses an HTTP method that function accepts.

`frappe.xcall` and `frappe.call` send POST unless told otherwise. A function whitelisted for GET only then
answers "Not permitted", and the feature behind it silently disappears: the "Request response" button on
Job Offer and Purchase Order never showed, because `rule_status` is GET-only and the script sent POST
(found 27 November 2026). This test reads the scripts and the Python decorators, without Frappe."""
import ast
from pathlib import Path
import re
import unittest

APP = Path(__file__).resolve().parents[1] / 'erpnext_drive_integrations'
PACKAGE = 'erpnext_drive_integrations'
ALL = {'GET', 'POST', 'PUT', 'DELETE'}
CALL = re.compile(r'frappe\s*\.\s*(xcall|call)\s*\(')  # also `frappe\n\t.xcall(` across lines
STRING = re.compile(r'''^\s*(["'])(.*?)\1\s*$''', re.S)


def whitelisted():
    """Dotted path -> set of HTTP methods for every @frappe.whitelist function in the app."""
    found = {}
    for path in APP.rglob('*.py'):
        module = '.'.join(path.relative_to(APP.parent).with_suffix('').parts)
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                target = deco.func if isinstance(deco, ast.Call) else deco
                if not (isinstance(target, ast.Attribute) and target.attr == 'whitelist'):
                    continue
                methods = ALL
                for keyword in getattr(deco, 'keywords', []):
                    if keyword.arg == 'methods':
                        methods = {item.value.upper() for item in keyword.value.elts}
                found[f'{module}.{node.name}'] = methods
    return found


def arguments(text, start):
    """Split the call starting just after '(' at `start` into its top-level argument strings."""
    depth, quote, args, current, i = 0, None, [], '', start
    while i < len(text):
        ch = text[i]
        if quote:
            current += ch
            if ch == '\\':
                current += text[i + 1]; i += 1
            elif ch == quote:
                quote = None
        elif ch in '"\'`':
            quote = ch; current += ch
        elif ch in '([{':
            depth += 1; current += ch
        elif ch in ')]}':
            if depth == 0:
                args.append(current)
                return args
            depth -= 1; current += ch
        elif ch == ',' and depth == 0:
            args.append(current); current = ''
        else:
            current += ch
        i += 1
    raise ValueError('unclosed call')


def calls():
    """(file, dotted method, HTTP method) for every literal call to one of our functions."""
    for path in APP.rglob('*.js'):
        text = path.read_text()
        for match in CALL.finditer(text):
            args = arguments(text, match.end())
            if match.group(1) == 'xcall':
                name = STRING.match(args[0]) if args else None
                kind = STRING.match(args[2]) if len(args) > 2 else None
            else:
                body = args[0] if args else ''
                name = re.search(r'''\bmethod\s*:\s*(["'])([\w.]+)\1''', body)
                kind = re.search(r'''\btype\s*:\s*(["'])(\w+)\1''', body)
            if name and name.group(2).startswith(PACKAGE + '.'):
                yield path.relative_to(APP.parent), name.group(2), (kind.group(2).upper() if kind else 'POST')


class BrowserCallMethodTests(unittest.TestCase):
    def test_every_call_uses_an_accepted_method(self):
        functions = whitelisted()
        seen = 0
        for path, name, method in calls():
            seen += 1
            with self.subTest(file=str(path), method=name):
                self.assertIn(name, functions, f'{path} calls {name}, which is not a whitelisted function')
                self.assertIn(method, functions[name],
                              f'{path} sends {method} to {name}, which accepts only {sorted(functions[name])}')
        self.assertGreaterEqual(seen, 6, 'the scan found fewer calls than the scripts make')

    def test_request_button_asks_with_get(self):
        found = {name: method for _, name, method in calls()}
        self.assertEqual(found[PACKAGE + '.onboarding.respond.rule_status'], 'GET')
        self.assertEqual(whitelisted()[PACKAGE + '.onboarding.respond.rule_status'], {'GET'})


if __name__ == '__main__':
    unittest.main()
