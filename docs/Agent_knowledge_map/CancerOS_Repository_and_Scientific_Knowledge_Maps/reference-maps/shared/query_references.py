#!/usr/bin/env python3
"""Look up a stable CancerOS behavior ID or substring in both reference maps."""
import argparse,json,pathlib
P=pathlib.Path(__file__).resolve().parent
read=lambda x:json.loads(x.read_text(encoding='utf-8'))
a=argparse.ArgumentParser();a.add_argument('query');a.add_argument('--json',action='store_true');args=a.parse_args()
B=read(P/'../scientific-map/behavior-to-evidence.json');R=read(P/'../repository-map/repository-register.json');A=read(P/'../scientific-map/academic-source-register.json');PP=read(P/'../scientific-map/research-paper-register.json')
rd={x['id']:x for x in R}; ad={x['id']:x for x in A}; pd={x['id']:x for x in PP}
q=args.query.casefold();matches=[b for b in B if q in b['id'].casefold() or q in b['title'].casefold() or q in b['intended_behavior'].casefold()]
if args.json:print(json.dumps([{'behavior':b,'academic':[ad[x] for x in b['academic_sources'] if x in ad],'papers':[pd[x] for x in b['papers'] if x in pd],'repositories':[rd[x] for x in b['implementations'] if x in rd]} for b in matches],indent=2));raise SystemExit(0)
if not matches:print('No mapped behavior found; use source specifications and record an unmapped task.');raise SystemExit(1)
for b in matches:
 print('\n==',b['id'],b['title'],'==\nIntent:',b['intended_behavior'],'\nTest:',b['verification'])
 for id in b['academic_sources']:
  if id in ad:
   s=ad[id];print(' BOOK/LECTURE',id,s['title'],'|',s['reading_locator'],'|',s['url'],'|',s.get('locator_status'))
 for id in b['papers']:
  if id in pd:print(' PAPER',id,pd[id]['title'],'|',pd[id].get('url'))
 for id in b['implementations']:
  if id in rd:
   r=rd[id];print(' REPOSITORY',id,r['name'],'|',r['url'],'\n  Inspect:',r['read_locations'],'\n  Reuse:',r['adopt_or_adapt'],'\n  Avoid:',r['avoid'],'\n  Verify:',r['required_test'])
