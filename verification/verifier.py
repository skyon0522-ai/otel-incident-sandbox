from pathlib import Path
import json,os,subprocess,sys,signal,socket,select,re,time,datetime,hashlib,shutil,difflib
from urllib.parse import urlparse
STAGE=Path(__file__).resolve().parent
EMAIL='customer.synthetic@example.test';TOKEN='synthetic-token-DO-NOT-USE-5f7d'
def objects(text):
    return [json.loads(line) for line in text.splitlines() if line.startswith('{')]
def attr(span,key):
    for item in span.get('Attributes',[]):
        if item.get('Key')==key:
            value=item.get('Value');return value.get('Value') if isinstance(value,dict) else value
    return None
def check(case):
    raw={k:(case/(k+'.log')).read_text() for k in ['server.stdout','server.stderr','client.stdout','client.stderr']}
    cs=[s for s in objects(raw['client.stdout']) if 'SpanContext' in s]
    ss=[s for s in objects(raw['server.stdout']) if 'SpanContext' in s]
    headers=objects((case/'outbound-headers.jsonl').read_text())
    received=[x for x in objects(raw['server.stderr']) if x.get('kind')=='received_headers']
    lifecycle=json.loads((case/'processes.json').read_text())
    app=[s for s in cs if s.get('SpanKind')==1];clients=[s for s in cs if s.get('SpanKind')==3]
    counts=len(cs)==4 and len(ss)==2 and len(app)==2 and len(clients)==2 and all(s.get('SpanKind')==2 for s in ss)
    statuses=counts and sorted(attr(s,'http.response.status_code') for s in clients)==[200,503] and sorted(attr(s,'http.response.status_code') for s in ss)==[200,503]
    if statuses:
        statuses=all(s['Status']['Code']==('Error' if attr(s,'http.response.status_code')==503 else 'Unset') for s in clients+ss)
    correlation=counts and len(headers)==2 and len({a['SpanContext']['TraceID'] for a in app})==2 and all(a['Name']=='support.request' for a in app)
    links=[]
    if correlation:
        for c in clients:
            sc=c['SpanContext'];parent=c['Parent'];servers=[s for s in ss if s['SpanContext']['TraceID']==sc['TraceID']]
            roots=[a for a in app if a['SpanContext']['SpanID']==parent['SpanID'] and a['SpanContext']['TraceID']==sc['TraceID']]
            wire=[h for h in headers if h['headers'].get('Traceparent',[''])[0].split('-')[1:3]==[sc['TraceID'],sc['SpanID']]]
            valid=len(servers)==1 and len(roots)==1 and len(wire)==1 and servers[0]['Parent']['SpanID']==sc['SpanID'] and servers[0]['Parent']['TraceID']==sc['TraceID'] and servers[0]['Parent']['Remote'] is True and attr(servers[0],'http.response.status_code')==attr(c,'http.response.status_code')
            correlation=correlation and valid
            links.append({'status':attr(c,'http.response.status_code'),'trace_id':sc['TraceID'],'client_span_id':sc['SpanID'],'server_parent_id':servers[0]['Parent']['SpanID'] if servers else None,'matches':valid})
    header_text=json.dumps(headers)
    checks={'process_lifecycle':lifecycle['server_exit']==0 and lifecycle['client_exit']==0 and lifecycle['server_pid']!=lifecycle['client_pid'] and lifecycle['listener_closed'] and lifecycle['server_stopped'] and lifecycle['client_stopped'],'response_statuses':[int(x.split()[1]) for x in raw['client.stdout'].splitlines() if x.startswith('STATUS ')]==[200,503],'completeness':counts,'status':bool(statuses),'correlation':bool(correlation),'privacy_headers':len(headers)==2 and all('baggage' not in {k.lower() for k in h['headers']} for h in headers) and EMAIL not in header_text and TOKEN not in header_text,'wire_no_baggage':len(received)==2 and all(x['baggage_present'] is False for x in received),'privacy_exported':all(EMAIL not in x and TOKEN not in x for x in raw.values())}
    result={'checks':checks,'pass':all(checks.values()),'client_span_count':len(cs),'server_span_count':len(ss),'trace_links':links,'failed_checks':[k for k,v in checks.items() if not v]}
    (case/'contract.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if len(sys.argv)>2 and sys.argv[1]=='--check':
    result=check(Path(sys.argv[2]));print(json.dumps(result));raise SystemExit(0 if result['pass'] else 1)
base=json.loads((STAGE/'baseline-runtime.json').read_text());env=os.environ.copy();env.update(base['environment'])
go=base['go_binary'];run=Path(json.loads((STAGE/'adapted-last-run.json').read_text())['run_directory'])
copy=STAGE/'copied/upstream/instrumentation/net/http/otelhttp';temporary=run/'_temporary';summary={'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':[],'build_commands':[]}
def command(label,args,cwd,folder):
    p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=240)
    (folder/(label+'.stdout')).write_text(p.stdout);(folder/(label+'.stderr')).write_text(p.stderr)
    record={'label':label,'argv':args,'cwd':str(cwd),'exit':p.returncode};summary['build_commands'].append(record)
    if p.returncode:raise RuntimeError(label+': '+p.stderr[-2500:])
    return p.stdout
def run_case(name,source,binaries):
    case=run/name;case.mkdir(exist_ok=False)
    for side in ['server','client']:
        command(side+'-build-metadata',[go,'version','-m',str(binaries/side)],source,case)
    mapping=json.loads(command('module',[go,'list','-m','-json','go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp'],source,case))
    if Path(mapping['Replace']['Dir']).resolve()!=copy.resolve():raise RuntimeError('Wrong copied implementation mapping')
    server=subprocess.Popen([str(binaries/'server')],cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    client=None;first='';clientout='';clienterr='';serverout='';servererr='';port=None
    try:
        ready,_,_=select.select([server.stdout],[],[],8)
        if not ready:raise RuntimeError('Server readiness timeout')
        first=server.stdout.readline()
        if not first.startswith('LISTEN '):raise RuntimeError('Missing loopback listener readiness: '+first)
        endpoint=first.strip().split(' ',1)[1];parsed=urlparse(endpoint)
        if parsed.hostname!='127.0.0.1':raise RuntimeError('Non-loopback listener')
        port=parsed.port
        client_args=[str(binaries/'client'),'--server',endpoint,'--headers',str(case/'outbound-headers.jsonl')]
        client=subprocess.Popen(client_args,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        clientout,clienterr=client.communicate(timeout=12)
        server.send_signal(signal.SIGTERM)
        serverout,servererr=server.communicate(timeout=10)
    finally:
        for p in [client,server]:
            if p is not None and p.poll() is None:
                p.kill();p.communicate(timeout=3)
    for name_,value in [('server.stdout',first+serverout),('server.stderr',servererr),('client.stdout',clientout),('client.stderr',clienterr)]:
        (case/(name_+'.log')).write_text(value)
    with socket.socket() as probe:
        probe.settimeout(1);closed=probe.connect_ex(('127.0.0.1',port))!=0
    lifecycle={'server_pid':server.pid,'client_pid':client.pid,'server_exit':server.returncode,'client_exit':client.returncode,'server_stopped':server.poll() is not None,'client_stopped':client.poll() is not None,'listener':'127.0.0.1:'+str(port),'listener_closed':closed,'server_argv':[str(binaries/'server')],'client_argv':client_args,'cwd':str(source),'termination':'SIGTERM then bounded graceful shutdown; post-exit connection probe'}
    (case/'processes.json').write_text(json.dumps(lifecycle,indent=2)+'\n')
    checker=subprocess.run([sys.executable,'-B',str(Path(__file__)),'--check',str(case)],capture_output=True,text=True,timeout=10)
    (case/'checker.stdout').write_text(checker.stdout);(case/'checker.stderr').write_text(checker.stderr)
    result=json.loads(checker.stdout)
    record={'case':name,'checker_exit':checker.returncode,'contract':result,'lifecycle':lifecycle,'module_mapping':mapping}
    summary['cases'].append(record)
    (run/'verification-runtime.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'case':name,'checker_exit':checker.returncode,'failed_checks':result['failed_checks'],'client_spans':result['client_span_count'],'server_spans':result['server_span_count']}),flush=True)
    return result,checker.returncode
try:
    positive,code=run_case('positive',STAGE/'adapted/example',run/'bin')
    if code:raise RuntimeError('Positive contract failed: '+str(positive['failed_checks']))
    for name,expected in [('baggage_leak','privacy_exported'),('no_extraction','correlation'),('drop_spans','completeness')]:
        variant=temporary/name
        shutil.copytree(STAGE/'adapted',variant)
        root=variant/'example'
        mod=root/'go.mod';mod.write_text(re.sub(r'(?m)^replace go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp => .*$', 'replace go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp => '+str(copy),mod.read_text()))
        changes=[]
        for side in ['client','server']:
            p=root/side/(side+'.go');old=p.read_text();new=old
            if name=='baggage_leak':
                new=new.replace('otel.SetTextMapPropagator(propagation.TraceContext{})','otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))')
                if side=='server':
                    new=new.replace('"go.opentelemetry.io/otel"','"go.opentelemetry.io/otel"\n\t"go.opentelemetry.io/otel/attribute"\n\t"go.opentelemetry.io/otel/baggage"')
                    new=new.replace('span.AddEvent("support request handled")','bag := baggage.FromContext(req.Context())\n\t\tspan.AddEvent("support request handled", trace.WithAttributes(attribute.String("customer_email", bag.Member("username").Value()), attribute.String("api_token", bag.Member("api_token").Value())))')
            elif name=='no_extraction' and side=='server':
                new=new.replace('otel.SetTextMapPropagator(propagation.TraceContext{})','otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator())')
            elif name=='drop_spans':
                new=new.replace('sdktrace.WithSampler(sdktrace.AlwaysSample())','sdktrace.WithSampler(sdktrace.NeverSample())')
            p.write_text(new)
            if new!=old:changes.append({'path':side+'/'+side+'.go','before_sha256':hashlib.sha256(old.encode()).hexdigest(),'after_sha256':hashlib.sha256(new.encode()).hexdigest(),'diff':''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True)))})
        (run/(name+'-mutation.json')).write_text(json.dumps({'expected_failed_check':expected,'changes':changes},indent=2)+'\n')
        binaries=variant/'bin';binaries.mkdir()
        for side in ['server','client']:
            command(name+'-'+side+'-build',[go,'build','-o',str(binaries/side),'./'+side],root,run)
        result,code=run_case(name,root,binaries)
        if code!=1 or result['checks'][expected]:raise RuntimeError('Negative control not detected: '+name)
    summary['all_expected_outcomes_observed']=True
finally:
    if temporary.exists():
        resolved=temporary.resolve()
        if not resolved.is_relative_to(run.resolve()) or resolved==run.resolve():raise RuntimeError('Unsafe disposable cleanup path')
        shutil.rmtree(resolved)
    summary['disposable_variants_removed']=not temporary.exists()
    summary['finished_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    provenance=json.loads((STAGE/'source-provenance.json').read_text())
    summary['original_copied_sources_unchanged']=all(hashlib.sha256((STAGE/k/'upstream'/f['path']).read_bytes()).hexdigest()==f['sha256'] for k in ['original','copied'] for f in provenance['source_files'])
    summary['adapted_source_sha256']={str(p.relative_to(STAGE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'adapted').rglob('*') if p.is_file()}
    (run/'verification-runtime.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'complete':True,'all_expected_outcomes_observed':summary.get('all_expected_outcomes_observed',False),'source_unchanged':summary['original_copied_sources_unchanged'],'run_directory':str(run)}),flush=True)
