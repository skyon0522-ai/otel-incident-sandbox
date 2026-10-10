# Copyright (c) 2026 OTel Incident Sandbox contributors
# SPDX-License-Identifier: MIT
"""Linux-only layout/build adapter for the byte-identical retained verifier."""
from pathlib import Path
import argparse,datetime,errno,hashlib,json,os,shutil,socket,subprocess,sys
REPO=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir',required=True,help='new directory outside this repository')
    parser.add_argument('--go',default=shutil.which('go'),help='existing Go executable')
    args=parser.parse_args()
    if sys.platform!='linux':raise SystemExit('This entry point is tested on Linux only')
    if not args.go:raise SystemExit('Provide an existing Go executable with --go or PATH')
    go=Path(args.go).resolve();work=Path(args.work_dir).resolve()
    if not go.is_file():raise SystemExit('Go executable does not exist')
    if work.exists() or work.is_relative_to(REPO):raise SystemExit('Work directory must be new and outside this repository')
    manifest=json.loads((REPO/'source-manifest.json').read_text())
    for f in manifest['files']:
        if hashlib.sha256((REPO/'upstream'/f['path']).read_bytes()).hexdigest()!=f['sha256']:raise SystemExit('Copied source hash mismatch')
    accepted=json.loads((REPO/'verification/derivation.json').read_text())['accepted_verifier_sha256']
    verifier=(REPO/'verification/verifier.py').read_bytes()
    if hashlib.sha256(verifier).hexdigest()!=accepted:raise SystemExit('Retained verifier hash mismatch')
    work.mkdir(parents=True)
    run=work/'verification-runs/run';(run/'bin').mkdir(parents=True)
    env=os.environ.copy();cache=work/'.go-cache'
    configuration={'GOWORK':'off','GOTOOLCHAIN':'local','GOFLAGS':'-mod=readonly','GOMODCACHE':str(cache/'modules'),'GOCACHE':str(cache/'build'),'GOPATH':str(cache/'gopath'),'GOPROXY':os.environ.get('GOPROXY','https://proxy.golang.org'),'GOSUMDB':'sum.golang.org','GODEBUG':'netdns=cgo'}
    env.update(configuration)
    receipt={'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python_version':sys.version.split()[0],'repository':str(REPO),'workspace':str(work),'fresh_cache_initially_absent':not cache.exists(),'commands':[],'verifier_sha256':accepted}
    def command(label,argv,cwd):
        print(json.dumps({'step':label,'start':True}),flush=True)
        p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True,timeout=600)
        (run/(label+'.stdout')).write_text(p.stdout);(run/(label+'.stderr')).write_text(p.stderr)
        receipt['commands'].append({'label':label,'argv':argv,'cwd':str(cwd),'exit':p.returncode})
        (work/'entrypoint-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({'step':label,'exit':p.returncode}),flush=True)
        if p.returncode:raise SystemExit(p.stderr[-3000:] or p.stdout[-3000:])
        return p.stdout
    receipt['go_version']=command('go-version',[str(go),'version'],work).strip()
    for f in manifest['files']:
        dst=work/'original/upstream'/f['path'];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((REPO/'upstream'/f['path']).read_bytes())
    (work/'copied').mkdir();(work/'copied/upstream').symlink_to(REPO/'upstream',target_is_directory=True)
    shutil.copytree(REPO/'example',work/'adapted/example')
    (work/'adapted/upstream').symlink_to(REPO/'upstream',target_is_directory=True)
    shutil.copyfile(REPO/'upstream/LICENSE',work/'adapted/LICENSE')
    (work/'verify_adapted.py').write_bytes(verifier)
    (work/'source-provenance.json').write_text(json.dumps({'source_files':manifest['files']},indent=2)+'\n')
    (work/'baseline-runtime.json').write_text(json.dumps({'purpose':'compatibility environment only; no baseline test rerun','go_binary':str(go),'environment':configuration},indent=2)+'\n')
    (work/'adapted-last-run.json').write_text(json.dumps({'run_directory':str(run)},indent=2)+'\n')
    example=work/'adapted/example'
    mapping=json.loads(command('local-module',[str(go),'list','-m','-json','go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp'],example))
    if Path(mapping['Replace']['Dir']).resolve()!=(REPO/'upstream/instrumentation/net/http/otelhttp').resolve():raise SystemExit('Wrong staged source mapping')
    receipt['resolved_copied_source']=str(Path(mapping['Replace']['Dir']).resolve())
    for side in ['server','client']:command(side+'-build',[str(go),'build','-o',str(run/'bin'/side),'./'+side],example)
    command('retained-verifier',[sys.executable,'-B',str(work/'verify_adapted.py')],work)
    command('modules-verify',[str(go),'mod','verify'],example)
    command('module-list',[str(go),'list','-m','-json','all'],example)
    runtime=json.loads((run/'verification-runtime.json').read_text())
    teardown=[]
    for case in runtime['cases']:
        life=case['lifecycle'];present=[]
        for pid in [life['server_pid'],life['client_pid']]:
            try:os.kill(pid,0);present.append(pid)
            except ProcessLookupError:pass
        host,port=life['listener'].split(':')
        with socket.socket() as probe:probe.settimeout(1);code=probe.connect_ex((host,int(port)))
        teardown.append({'case':case['case'],'owned_pids_present':present,'listener':life['listener'],'connect_errno':code})
    if any(t['owned_pids_present'] or t['connect_errno']!=errno.ECONNREFUSED for t in teardown):raise SystemExit('Teardown inspection failed')
    receipt['teardown']=teardown
    receipt['all_expected_outcomes_observed']=runtime['all_expected_outcomes_observed']
    receipt['staged_47_source_files_unchanged']=all(hashlib.sha256((REPO/'upstream'/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in manifest['files'])
    receipt['binaries_sha256']={side:hashlib.sha256((run/'bin'/side).read_bytes()).hexdigest() for side in ['server','client']}
    sums={(m,v):h for m,v,h in [line.split() for line in (REPO/'example/go.sum').read_text().splitlines()]}
    downloads=[]
    for zipfile in (cache/'modules/cache/download').rglob('*.zip'):
        relative=zipfile.relative_to(cache/'modules/cache/download');module=str(relative).split('/@v/')[0];version=zipfile.stem;h1=zipfile.with_suffix('.ziphash').read_text().strip()
        downloads.append({'module':module,'version':version,'zip_sha256':hashlib.sha256(zipfile.read_bytes()).hexdigest(),'cached_h1':h1,'original_go_sum_h1':sums.get((module,version)),'matches_original_go_sum':h1==sums.get((module,version))})
    if not all(d['matches_original_go_sum'] for d in downloads):raise SystemExit('Original dependency checksum mismatch')
    receipt['downloaded_modules']=downloads
    receipt['finished_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (work/'entrypoint-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'all_expected_outcomes_observed':receipt['all_expected_outcomes_observed'],'source_unchanged':receipt['staged_47_source_files_unchanged'],'receipt':str(work/'entrypoint-receipt.json')}),flush=True)
if __name__=='__main__':main()

