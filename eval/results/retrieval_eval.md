# Retrieval evaluation

48 in-scope questions (gold = correct documents), 12 out-of-scope questions.
hit@k and MRR are per document (duplicate chunks of one document removed). **chunk hit@4** counts the first 4 chunks, exactly what the LLM receives (top_k = 4).

| Setup | chunk hit@4 | hit@1 | hit@4 | hit@10 | MRR | ms/query |
|---|---|---|---|---|---|---|
| BM25 | **0.79** | 0.58 | 0.83 | 0.88 | 0.696 | 4 |
| Dense bge-small | **0.79** | 0.62 | 0.83 | 0.83 | 0.707 | 11 |
| Dense granite-small-r2 | **0.73** | 0.58 | 0.77 | 0.79 | 0.672 | 11 |
| Hybrid BM25+bge | **0.85** | 0.75 | 0.92 | 0.94 | 0.818 | 18 |
| Hybrid BM25+granite | **0.88** | 0.71 | 0.90 | 0.92 | 0.792 | 18 |

## chunk hit@4 by question type

| Setup | id_lookup (n=8) | procedure (n=20) | symptom (n=20) |
|---|---|---|---|
| BM25 | 1.00 | 0.75 | 0.75 |
| Dense bge-small | 0.38 | 0.90 | 0.85 |
| Dense granite-small-r2 | 0.12 | 0.85 | 0.85 |
| Hybrid BM25+bge | 0.88 | 0.85 | 0.85 |
| Hybrid BM25+granite | 0.88 | 0.85 | 0.90 |

## Best dense cosine score (for the refusal threshold)

| Embedder | in-scope min / median | out-of-scope median / max |
|---|---|---|
| BAAI/bge-small-en-v1.5 | 0.609 / 0.745 | 0.507 / 0.641 |
| ibm-granite/granite-embedding-small-english-r2 | 0.830 / 0.877 | 0.747 / 0.841 |

## Misses of the best setup (Hybrid BM25+granite): no correct chunk among the 4 sent to the LLM

| id | question | first correct chunk | first correct doc | retrieved top 3 docs |
|---|---|---|---|---|
| id06 | Which tactic does T1548.002 belong to? | 5 | 2 | austinsonger:T1566-Phishing-T1566.001-T1566.002-T1566.003, attack:T1548.002, attack:T1588 |
| sy18 | Gigabytes of internal files were uploaded to a public file-sharing site | >30 | >10 | attack:T1027.001, attack:T1135, attack:T1213 |
| sy19 | Malicious code was written into the memory of explorer.exe and run there | >30 | >10 | attack:T1027.016, attack:T1036.007, attack:T1574.014 |
| pr06 | How do I investigate a possibly compromised Linux server? | 7 | 6 | counteractive:playbook-defacement, attack:T1584.003, attack:T1584.004 |
| pr12 | A supplier with VPN access to our network was hacked. What now? | >30 | >10 | austinsonger:Best-Practices-Prior-to-an-Incident, certsg:IRM-11-InformationLeakage, certsg:IRM-18-Large-scale-compromise |
| pr16 | Someone threatens to leak our data unless we pay them | >30 | >10 | attack:T1657, certsg:IRM-11-InformationLeakage, counteractive:playbook-defacement |
