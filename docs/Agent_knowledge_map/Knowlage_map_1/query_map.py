#!/usr/bin/env python3
"""Search and expand CancerOS knowledge graph. Example: python query_map.py IMG.MESH"""
import json,sys,pathlib
path=pathlib.Path(__file__).parent/'canceros-knowledge-graph.json'
g=json.loads(path.read_text())
q=' '.join(sys.argv[1:]).lower().strip()
if not q:raise SystemExit('usage: python query_map.py NODE_ID or keywords')
idx={n['id']:n for n in g['nodes']}
match=[n for n in g['nodes'] if q in (n['id']+' '+n['title']+' '+n['description']).lower()]
if not match:raise SystemExit('No matching nodes')
for n in match[:12]:
 print('\n===',n['id'],n['title'],'===\n',n['description'],'\nSources:',','.join(n['source_documents']))
 for e in g['edges']:
  if e['from_id']==n['id']:print('  -->',e['relation'],e['to_id'],idx[e['to_id']]['title'])
  if e['to_id']==n['id']:print('  <--',e['relation'],e['from_id'],idx[e['from_id']]['title'])
