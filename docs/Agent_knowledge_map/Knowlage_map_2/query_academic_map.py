#!/usr/bin/env python3
import json,sys,pathlib
p=pathlib.Path(__file__).with_name('knowledge-map.json')
g=json.loads(p.read_text()); n={x['id']:x for x in g['nodes']}
q=' '.join(sys.argv[1:]).lower().strip()
if not q:
 print('Usage: python query_academic_map.py IMG.10 | registration | SIM.02'); sys.exit(0)
found=[x for x in g['nodes'] if x['type']=='behavior' and (q in x['id'].lower() or q in x['title'].lower() or q in x['design_decision'].lower())]
for x in found:
 print('\n'+x['id']+' — '+x['title']+'\nDesign: '+x['design_decision']+'\nAcceptance: '+x['verification'])
 for k,label in [('academic_sources','READ'),('repository_references','REPO'),('paper_references','PAPER')]:
  for sid in x[k]:
   z=n[sid];print('  '+label+' '+sid+' '+z['title']+' — '+z.get('reading_locator',z.get('reference_role',''))+' — '+z['url'])
if not found: print('No matching behavior. Try a shorter search term.')
