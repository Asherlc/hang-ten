import math,uuid

def audit(rows,schema,targetEpoch):
 errors=[];contexts={};attempts={};loads={};spans=[];pending={};markers=[];loadReturns={};deferred=set()
 def fail(r,reason):errors.append(dict(sequence=r.get('sequence'),event=r.get('event'),reason=reason))
 def valid(value,kind):
  if kind.startswith('nullable'):
   if value is None:return True
   kind={'nullableUUID':'UUID','nullableFinite':'finite'}[kind]
  if kind=='string':return isinstance(value,str) and bool(value)
  if kind=='bool':return type(value) is bool
  if kind=='integer':return type(value) is int
  if kind=='finite':return type(value) in (int,float) and math.isfinite(value)
  if kind=='UUID':
   try:return isinstance(value,str) and str(uuid.UUID(value)).lower()==value.lower()
   except (ValueError,TypeError,AttributeError):return False
  return False
 def known_attempt(r,ident):
  if ident not in attempts:fail(r,'unknown attempt '+str(ident));return False
  if attempts[ident]['contextID']!=r['contextID']:fail(r,'attempt context mismatch');return False
  return True
 # The full opening stream is used: pre-appearance load calls/context markers remain relevant.
 for r in rows:
  if not str(r.get('event','')).startswith('startup-'):continue
  if targetEpoch is not None and type(r.get('epoch')) in (int,float) and r['epoch']>targetEpoch:continue
  markers.append(r);event=r['event'];fields=schema['events'].get(event)
  if fields is None:fail(r,'unknown startup event');continue
  types=dict(fields,epoch='finite',uptime='finite',sequence='integer')
  invalid=[key for key,kind in types.items() if key not in r or not valid(r[key],kind)]
  if invalid:fail(r,'invalid/missing scalar fields '+','.join(invalid));continue
  if event=='startup-association-ambiguous':fail(r,'explicit correlation ambiguity: '+r['reason'])
  if 'associationValid' in r and r['associationValid'] is not True:fail(r,'associationValid false')
  context=r.get('contextID')
  if event=='startup-context-appear':
   if context in contexts or r['appearanceCount']!=1:fail(r,'duplicate context appearance')
   contexts[context]=r
   if len(contexts)!=1:fail(r,'multiple workout contexts')
  elif context is not None and context not in contexts:fail(r,'unknown context')
  if event=='startup-request-entry':
   ident=r['attemptID'];parent=r['parentAttemptID']
   if ident is None or ident in attempts:fail(r,'missing/duplicate request attempt')
   else:
    if parent is not None:known_attempt(r,parent)
    attempts[ident]=r
  elif 'attemptID' in r:
   ident=r['attemptID']
   if ident is None:
    if event!='startup-audio-preparation-change':fail(r,'missing required attempt association')
   elif known_attempt(r,ident) and attempts[ident]['parentAttemptID']!=r['parentAttemptID']:fail(r,'parent attempt changed')
  if event=='startup-request-deferred':deferred.add(r['attemptID'])
  if event=='startup-deferred-dispatch':
   if r['attemptID'] not in deferred:fail(r,'unknown deferred dispatch association')
   else:deferred.remove(r['attemptID'])
  if event=='startup-cancellation-requested':
   for present,key in [('taskPresent','armedAttemptID'),('pendingPresent','deferredAttemptID')]:
    ident=r[key]
    if r[present] and ident is None:fail(r,'missing cancellation target '+key)
    if ident is not None:known_attempt(r,ident)
  if event=='startup-board-load-call':
   ident=r['loadAttempt']
   if ident in loads:fail(r,'duplicate load UUID')
   else:loads[ident]=r
  elif event.startswith('startup-board-'):
   if r['loadAttempt'] not in loads:fail(r,'unknown load UUID')
  if event=='startup-board-load-return':
   token=r['sceneLifecycleToken']
   ctors=[x for x in rows if x.get('event')=='board-scene-constructed' and x.get('sceneLifecycleToken')==token and x['sequence']<r['sequence']]
   if len(ctors)!=1:fail(r,'load return lacks unique earlier model constructor identity')
   loadReturns[r['loadAttempt']]=r
  if event=='startup-board-ready-published':
   returned=loadReturns.get(r['loadAttempt'])
   if returned is None or returned['sceneLifecycleToken']!=r['sceneLifecycleToken']:fail(r,'ready marker unknown or changed returned scene identity')
  # Explicit schema pairs only; no inference from event spelling, no required end event.
  for definition in schema.get('spans',[]):
   if event not in [definition['beginEvent'],*definition['endEvents']]:continue
   key=(definition['name'],*(r.get(k) for k in definition['identityFields']))
   if event==definition['beginEvent']:
    if key in pending:fail(r,'duplicate unfinished span '+definition['name'])
    pending[key]=r
   else:
    before=pending.pop(key,None)
    if before is None:fail(r,'unknown span beginning '+definition['name'])
    spans.append(dict(name=definition['name'],identity=list(key[1:]),begin=before,end=r,rightCensored=False))
 for key,r in pending.items():spans.append(dict(name=key[0],identity=list(key[1:]),begin=r,end=None,rightCensored=True,censorEpoch=targetEpoch))
 return dict(errors=errors,markers=markers,contexts=contexts,attempts=attempts,loads=loads,spans=spans)
