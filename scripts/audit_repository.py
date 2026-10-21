"""Audit Git's index for unwanted files, oversized blobs, credentials and broken doc links."""
import argparse
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]

def git(*args,input=None):
    return subprocess.run(['git',*args],cwd=ROOT,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout

def audit(limit):
    entries=[]
    for record in git('ls-files','--stage','-z').split(b'\0'):
        if not record:continue
        metadata,name=record.split(b'\t',1)
        mode,oid,stage=metadata.decode().split()
        entries.append((name.decode('utf-8'),oid,stage))
    if not entries:raise ValueError('Git index is empty; stage the reviewed source files first')
    names={row[0] for row in entries}
    request=('\n'.join(row[1] for row in entries)+'\n').encode()
    raw=git('cat-file','--batch',input=request)
    position=0;issues=[];sizes=[]
    blocked={'venv','.venv','.gpu-venv','__pycache__','.aws','.ssh','.codex','.agents','node_modules','storage','model-cache','models','run','artifacts','.cache','reports'}
    detectors={
        'private key':rb'-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----',
        'AWS access key':rb'\bAKIA[0-9A-Z]{16}\b',
        'GitHub token':rb'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b',
        'GitHub fine-grained token':rb'\bgithub_pat_[A-Za-z0-9_]{50,}\b',
        'Hugging Face token':rb'\bhf_[A-Za-z0-9]{30,}\b',
        'API secret token':rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b',
    }
    for path,oid,stage in entries:
        end=raw.index(b'\n',position);header=raw[position:end].split();size=int(header[2])
        content=raw[end+1:end+1+size];position=end+size+2;sizes.append((size,path))
        parts=path.lower().split('/')
        if stage!='0':issues.append(f'{path}: unresolved index stage')
        if any(part in blocked for part in parts):issues.append(f'{path}: local/generated/private directory')
        if parts[0]=='data' and (len(parts)!=2 or not (path.endswith('.py') or path=='data/README_datasets.md')):
            issues.append(f'{path}: dataset content must stay local')
        if size>limit:issues.append(f'{path}: {size} bytes exceeds repository file cap')
        if b'\0' not in content[:8192] and Path(path).suffix.lower() not in ('.pdf','.png','.jpg','.jpeg','.tif','.tiff'):
            for label,pattern in detectors.items():
                if re.search(pattern,content):issues.append(f'{path}: possible {label} (value omitted)')
        if path.endswith('.md'):
            text=re.sub(r'```.*?```','',content.decode('utf-8-sig'),flags=re.S)
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
                target=target.strip('<>')
                if target.startswith(('https://','http://','mailto:','#')):continue
                destination=unquote(target.split('#')[0])
                normalized=posixpath.normpath(posixpath.join(posixpath.dirname(path),destination))
                if normalized not in names:issues.append(f'{path}: link target is not committed: {target}')
    check=subprocess.run(['git','check-ignore','--no-index','--stdin','-z'],cwd=ROOT,input=('\0'.join(names)+'\0').encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if check.returncode not in (0,1):raise RuntimeError(check.stderr.decode())
    for path in check.stdout.decode().split('\0'):
        if path:issues.append(f'{path}: force-added despite .gitignore')
    for issue in issues:print('FAIL:',issue)
    print(f'Audited {len(entries)} indexed files, {sum(s for s,_ in sizes)/1024/1024:.2f} MiB total')
    print('Largest files:')
    for size,path in sorted(sizes,reverse=True)[:5]:print(f'  {size:>8} bytes  {path}')
    if issues:return 1
    print('Repository audit passed: no blocked paths, oversized files, detected credential patterns or broken local Markdown links.')
    return 0

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--max-file-mb',type=float,default=5);args=parser.parse_args()
    try:return audit(int(args.max_file_mb*1024*1024))
    except (ValueError,RuntimeError,subprocess.CalledProcessError) as exc:print('Audit failed:',exc);return 1

if __name__=='__main__':sys.exit(main())
