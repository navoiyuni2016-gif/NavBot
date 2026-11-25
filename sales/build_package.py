#!/usr/bin/env python3
"""Build a distributable source package from public assets only; never copy runtime data."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
# Explicit directory and extension allowlists; no .git, databases, tokens or tenant registries.
DEPLOY_ASSETS={'navbot-backup.py','NAVBOT-PRINT-AGENT.ps1','START-NAVBOT-NATIVE.ps1','START-NAVBOT-NATIVE.bat','NATIVE-PRINTER-README.txt','NAVBOT-START.html','INSTALL-NAVBOT-AUTOSTART.ps1','INSTALL-NAVBOT-AUTOSTART.bat','REMOVE-NAVBOT-AUTOSTART.bat','TEST-NAVBOT-WINDOWS.bat'}

RULES={
 'navbot':{'.py','.html','.css','.js','.json','.svg','.wav'},
 'sales':{'.py','.md'},
 'sales/examples':{'.json'},
 'deploy':{'.py','.md','.service','.timer','.conf','.ps1','.bat','.txt','.html'},
 'downloads':{'.apk','.zip'},
}


def sources(root=ROOT):
    root=Path(root);selected={}
    for directory,extensions in RULES.items():
        folder=root/directory
        paths=folder.rglob('*') if directory=='navbot' else folder.glob('*')
        for path in paths:
            relative=path.relative_to(root)
            if any(part.startswith('.') or part=='__pycache__' for part in relative.parts):continue
            if any(part.endswith('.integration-secrets') for part in relative.parts):continue
            if path.is_symlink():raise ValueError('Symlink excluded from sale package: '+str(relative))
            if not path.is_file() or path.suffix.lower() not in extensions:continue
            if directory=='deploy' and path.name not in DEPLOY_ASSETS:continue
            if directory=='downloads' and path.name!='NAVBOT-NATIVE.zip':continue
            if directory=='navbot' and path.suffix=='.json' and relative.as_posix()!='navbot/catalog.json':continue
            if directory=='navbot' and path.suffix=='.wav' and not (relative.as_posix()=='navbot/tv-tone.wav' or relative.parts[:3]==('navbot','voice','uz')):continue
            # Root named runtime configs are never package inputs.
            if path.name in ('printer-config.json','print-journal.json','startup-status.txt'):continue
            selected[relative.as_posix()]=path
    if not {'navbot/app.py','sales/tenant.py','sales/README.md'}<=set(selected):raise ValueError('Required package files missing')
    return selected


def build(output,root=ROOT):
    output=Path(output);files=sources(root);output.parent.mkdir(parents=True,exist_ok=True)
    manifest={'product':'NAVBOT','format':1,'deployment':'one-process-user-and-database-per-tenant','sha256':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sorted(files.items())}}
    manifest['release_id']=hashlib.sha256(json.dumps(manifest['sha256'],sort_keys=True).encode()).hexdigest()[:16]
    # Exclusive output prevents accidental overwrite of an already distributed release.
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,path in sorted(files.items()):
            info=zipfile.ZipInfo('NAVBOT-SALES/'+name);info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,path.read_bytes())
        archive.writestr('NAVBOT-SALES/PACKAGE-MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_text(digest+'  '+output.name+'\n')
    return manifest


def verify(archive_path):
    with zipfile.ZipFile(archive_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or any(Path(n).is_absolute() or '..' in Path(n).parts for n in names):raise ValueError('Unsafe package names')
        manifest=json.loads(archive.read('NAVBOT-SALES/PACKAGE-MANIFEST.json'))
        expected=manifest['sha256']
        actual={n.removeprefix('NAVBOT-SALES/'):hashlib.sha256(archive.read(n)).hexdigest() for n in names if n!='NAVBOT-SALES/PACKAGE-MANIFEST.json'}
        if actual!=expected:raise ValueError('Package contents/checksums differ')
        return len(actual)


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--output',type=Path);group.add_argument('--verify',type=Path);args=parser.parse_args()
    if args.verify:print('Package verified:',verify(args.verify),'files')
    else:build(args.output);print('Package created:',args.output)
