#!/usr/bin/env python3
"""Offline syntax, schema, import and publication checks. Never reads a live site."""
import argparse
import ast
import json
import pathlib
import re
import sys

SKIP=('.git','node_modules','__pycache__','.runtime','.build')


def check(root, deny=()):
    root=pathlib.Path(root);errors=[];count=0;sources=[]
    for p in root.rglob('*'):
        if not p.is_file() or any(x in p.parts for x in SKIP):
            continue
        if p.suffix not in {'.py','.js','.json','.ts','.tsx','.html','.md','.yml','.yaml','.toml','.svg','.txt','.sh'} and p.name not in {'Dockerfile','.env.example','.gitignore'}:
            continue
        text=p.read_text();count+=1
        for term in deny:
            if term and term.lower() in text.lower():errors.append(f'{p.relative_to(root)}: disallowed publication text')
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text):errors.append(f'{p.relative_to(root)}: private key')
        if re.search(r'(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}',text):errors.append(f'{p.relative_to(root)}: credential token')
        try:
            if p.suffix=='.py':sources.append((p,ast.parse(text,filename=str(p))))
            if p.suffix=='.json':json.loads(text)
        except (SyntaxError,ValueError) as exc:errors.append(f'{p.relative_to(root)}: {exc}')
    errors+=check_imports(root,sorted(sources))
    if errors:raise ValueError('\n'.join(errors))
    return count


# P68: imports of this repository's own modules -------------------------------------------------------------------
GUARDS={'ImportError','ModuleNotFoundError','Exception','BaseException'}


def module_file(base,dotted):
    """The file (or namespace folder) of a module under `base`, or None."""
    path=base.joinpath(*dotted.split('.'))
    for candidate in (path.with_suffix('.py'),path/'__init__.py'):
        if candidate.is_file():return candidate
    return path if path.is_dir() and any(path.glob('*.py')) else None


def top_level_names(tree):
    """Names a module defines at its top level (functions, classes, assignments, loop and `with` targets, imports,
    `global` names), and whether it defines names dynamically (`globals()`, a module `__getattr__`, `import *`)."""
    names=set();dynamic=False
    def visit(node):
        nonlocal dynamic
        for child in ast.iter_child_nodes(node):
            if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                names.add(child.name);dynamic|=child.name=='__getattr__'
                continue
            if isinstance(child,ast.Lambda):continue
            if isinstance(child,ast.Name) and isinstance(child.ctx,ast.Store):names.add(child.id)
            elif isinstance(child,(ast.Import,ast.ImportFrom)):
                for alias in child.names:
                    if alias.name=='*':dynamic=True
                    else:names.add(alias.asname or alias.name.split('.')[0])
            elif isinstance(child,ast.ExceptHandler) and child.name:names.add(child.name)
            visit(child)
    visit(tree)
    for node in ast.walk(tree):
        if isinstance(node,ast.Global):names.update(node.names)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='globals':dynamic=True
    return names,dynamic


def imports(node,guarded=False):
    """Every import, also inside functions (lazy imports), except those guarded by `except ImportError` (optional)."""
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        if not guarded:
            yield node
        return
    if isinstance(node, ast.Try) and any(
        handler.type is None or any(
            isinstance(name, ast.Name) and name.id in GUARDS for name in ast.walk(handler.type)
        )
        for handler in node.handlers
    ):
        for statement in node.body:
            yield from imports(statement, True)
        for statement in [*node.handlers, *node.orelse, *node.finalbody]:
            yield from imports(statement, guarded)
        return
    for child in ast.iter_child_nodes(node):
        yield from imports(child, guarded)


def check_imports(root,sources):
    """An import of this repository's own modules must name a module, and names, that exist. A lazy import of a
    missing name passes every test that fakes the module and fails only on the live site (P64, 21 November 2026)."""
    root=pathlib.Path(root);errors=[];defined={}
    def names_of(path):
        if path not in defined:
            defined[path]=top_level_names(ast.parse(path.read_text(encoding='utf-8'))) if path.suffix=='.py' else (set(),False)
        return defined[path]
    for path,tree in sources:
        rel=path.relative_to(root)
        for node in imports(tree):
            if isinstance(node,ast.Import):targets=[alias.name for alias in node.names];source=None
            elif node.level:
                package=list(rel.parent.parts)[:len(rel.parent.parts)-(node.level-1)]
                targets=['.'.join(package+([node.module] if node.module else []))];source=node
            else:targets=[node.module];source=node
            for dotted in targets:
                top=dotted.split('.')[0]
                # Scripts (tools/, tests/) also import their neighbours; modules inside a package only from the root.
                bases=(root,) if (path.parent/'__init__.py').is_file() else (path.parent,root)
                base=root if source is not None and source.level else next((b for b in bases if module_file(b,top)),None)
                if base is None:continue  # not ours (standard library, Frappe, other packages)
                found=module_file(base,dotted)
                if not found:
                    errors.append(f'{rel}:{node.lineno}: imports {dotted}, which does not exist');continue
                if source is None:continue
                names,dynamic=names_of(found)
                for alias in source.names:
                    if alias.name=='*' or dynamic or alias.name in names or module_file(base,f'{dotted}.{alias.name}'):continue
                    errors.append(f'{rel}:{node.lineno}: imports {alias.name} from {dotted}, which does not define it')
    return errors


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default=str(pathlib.Path(__file__).resolve().parents[1]));parser.add_argument('--deny-file');args=parser.parse_args()
    deny=json.loads(pathlib.Path(args.deny_file).read_text()) if args.deny_file else []
    print(f'Checked {check(args.root,deny)} source/doc files: passed')
