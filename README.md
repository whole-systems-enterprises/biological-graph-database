# biological-graph-database

Graph Database Builder for Biological Applications (particularly molecular biology applications)

This is basically where we are collecting all our Neo4j code for making general purpose, non-proprietary biological graph databases.

We started with NCBI's taxonomy and gene data.

## How to run this thing

You need a lot of memory...

```
mkdir output
mkdir output/gene_lists
mkdir data

cd data
mkdir taxonomy
cd taxonomy
wget ftp://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz
gunzip taxdump.tar.gz 
tar -xf taxdump.tar 
gzip taxdump.tar 
cd ..
cd ..

cd data
mkdir gene
cd gene
wget ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_info.gz
wget ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2go.gz
wget ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2pubmed.gz
gunzip gene_info.gz
gunzip gene2go.gz
gunzip gene2pubmed.gz
cd ..
cd ..

cd data
mkdir DisGeNET
cd DisGeNET
wget http://www.disgenet.org/ds/DisGeNET/files/current/disgenet_2017_v5-3-0.db.gz
gunzip disgenet_2017_v5-3-0.db.gz
cat ../../DisGeNET.sql | sqlite3 disgenet_2017_v5-3-0.db > relevant_db_dump.tsv
gzip disgenet_2017_v5-3-0.db
cd ..
cd ..


./packages/neo4j-community-3.3.3/bin/neo4j start

python3 load_taxonomy.py hostname password

python3 preprocess_gene_info.py

python3 load_gene.py hostname password

python3 load_and_link_synonyms.py hostname password

python3 link_genes_to_taxonomy.py hostname password
```

## Useful queries

### Boring queries

Find the taxonomy node for human:

```
MATCH (c:NCBI_TAXONOMY) WHERE c.id = 9606 RETURN c;
``

Find the taxonomy node for human, which specific attributes:
```
MATCH (c:NCBI_TAXONOMY) WHERE c.id = 9606 RETURN c.id AS NCBI_taxonomy_id, c.name AS scientific_name;
```

Find the NCBI gene synonym node 'A1B':
```
MATCH (n:NCBI_GENE_SYNONYM) WHERE n.symbol = "A1B" RETURN n;
```

### Slightly more interesting queries

Show taxonomy (should be 9606--human) and gene synonyms for human gene A1BG:
```
MATCH (g:NCBI_GENE)-[r1:HAS_NCBI_TAXONOMY]->(t:NCBI_TAXONOMY), (g)-[r2:HAS_NCBI_GENE_SYNONYM]->(gs:NCBI_GENE_SYNONYM), (gs)-[r3:HAS_NCBI_TAXONOMY]->(t) WHERE g.id = 1 RETURN g, r1, t, r2, gs, r3;
```
