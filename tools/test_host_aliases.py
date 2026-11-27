#!/usr/bin/env python3
"""Resolve this test host's own HTTPS services locally, retaining TLS checks.

This avoids public-IP hairpin failures for host-side enrollment. Public DNS and
the existing SSO hostname are unchanged. Only the instance's marked block changes.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re


def render(text,profile):
    if profile.get('tier')!='test':raise ValueError('Only test host aliases are supported')
    identifier=hashlib.sha256(profile['instance'].encode()).hexdigest()[:12]
    start='# cloud-test '+identifier+' begin';end='# cloud-test '+identifier+' end'
    if (start in text)!=(end in text):raise ValueError('Incomplete managed host block')
    clean=re.sub(re.escape(start)+r'\n.*?'+re.escape(end)+r'\n?', '',text,flags=re.S)
    hosts=[profile['hosts'][name] for name in ['erp','drive','office','mail','dms','respond']]
    hosts+=[profile['hosts'][name] for name in ['chat','chat-auth'] if name in profile['hosts']]
    if any(not re.fullmatch('[a-z0-9.-]+',host) for host in hosts):raise ValueError('Invalid test hostname')
    for line in clean.splitlines():
        values=line.split('#',1)[0].split()
        if set(values[1:])&set(hosts):raise ValueError('Existing unmanaged test host entry requires review')
    return clean.rstrip()+'\n'+start+'\n127.0.0.1 '+' '.join(hosts)+'\n'+end+'\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--profile',required=True)
    profile=json.loads(Path(parser.parse_args().profile).read_text())
    with Path('/run/cloud-test-hosts.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        file=Path('/etc/hosts');text=render(file.read_text(),profile)
        # Preserve the inode for hosts files provided through a host bind mount.
        with file.open('w') as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
    print('Local test HTTPS host aliases configured; public DNS unchanged')
