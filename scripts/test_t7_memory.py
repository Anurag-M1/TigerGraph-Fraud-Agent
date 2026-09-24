import sqlite3, json
from pathlib import Path

conn = sqlite3.connect('gsql/graph_data/fraud_graph.db')
cur = conn.cursor()

print('=== T7.1: INVESTIGATIONCASE VERTEX COUNT & EVIDENCE LINKS ===')
cur.execute('SELECT id FROM InvestigationCase WHERE id LIKE "CASE-HHG-%"')
cases_in_graph = [r[0] for r in cur.fetchall()]
print(f'Total InvestigationCase vertices in graph: {len(cases_in_graph)} (expected 20)')
assert len(cases_in_graph) == 20

# Check evidence edges per case
cases_with_evidence = []
for cid in cases_in_graph:
    cur.execute('SELECT count(*) FROM Edge_REFERENCES_EVIDENCE WHERE from_id = ?', (cid,))
    cnt = cur.fetchone()[0]
    if cnt > 0:
        cases_with_evidence.append(cid)
print(f'Cases with evidence linkages: {len(cases_with_evidence)} / {len(cases_in_graph)}')
assert len(cases_with_evidence) == len(cases_in_graph), 'Orphan cases found!'

print('\n=== T7.2: READ BACK ONE CASE (HHG-014) AND DIFF AGAINST JSON ===')
cur.execute('SELECT id, verdict, fraud_probability, pattern, exposure_usd, sar_filed FROM InvestigationCase WHERE id = "CASE-HHG-014"')
row = cur.fetchone()
print('Graph row:', row)

with open('cases/HHG-014.json') as f:
    json_data = json.load(f)
c = json_data['case']
sar = json_data['sar']

print('JSON attributes: verdict=', c['verdict'], 'prob=', c['fraud_probability'], 'pattern=', c['pattern'], 'exposure=', c['exposure_usd'], 'sar_filed=', sar['file'])
assert row[1] == c['verdict']
assert abs(row[2] - c['fraud_probability']) < 1e-4
assert row[3] == c['pattern']
assert abs(row[4] - c['exposure_usd']) < 0.01
assert bool(row[5]) == sar['file']
print('Diff check: 100% MATCH!')

print('\n=== T7.3: RETRIEVAL PROOF (CASE MEMORY LOOKUP) ===')
cur.execute('SELECT to_id FROM Edge_REFERENCES_EVIDENCE WHERE from_id = "CASE-HHG-014"')
ev_ids = [r[0] for r in cur.fetchall()]
print(f'HHG-014 evidence IDs: {ev_ids}')

cur.execute('SELECT id, pattern, verdict, exposure_usd FROM InvestigationCase WHERE verdict = "fraud"')
fraud_cases = cur.fetchall()
print(f'Total learned fraud cases in graph memory: {len(fraud_cases)}')
for fc in fraud_cases[:3]:
    print(f'  Memory hit: {fc[0]} | verdict={fc[1]} | pattern={fc[2]} | exposure=${fc[3]:.2f}')

print('\n=== T7.4: NO ORPHAN VERTICES ===')
cur.execute('''
    SELECT i.id 
    FROM InvestigationCase i 
    LEFT JOIN Edge_REFERENCES_EVIDENCE e ON i.id = e.from_id 
    WHERE e.to_id IS NULL AND i.id LIKE "CASE-HHG-%"
''')
orphans = cur.fetchall()
print(f'Orphan investigation cases (zero evidence edges): {len(orphans)}')
assert len(orphans) == 0

print('\nALL T7 CASE MEMORY TESTS PASSED!')
conn.close()
