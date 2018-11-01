
#
# import useful libraries
#
import pprint as pp
from neo4j import GraphDatabase
import sys
import utilities as ut

#
# user settings
#
username = 'neo4j'
password = sys.argv[2]
hostname = sys.argv[1]
uri = 'bolt://' + hostname + ':7687'

chunk_size = 5000
tax_id_to_keep = [9606]

#
# read the source file
#
gene_id_to_pubmed_id = {}
unique_pubmed_ids = {}
f = open('data/gene/gene2pubmed')
for line in f:
    line = [x.strip() for x in line.split('\t') if x.strip() != '']
    if line[0] == '#tax_id':
        continue

    tax_id = int(line[0])
    if not tax_id in tax_id_to_keep:
        continue

    gene_id = int(line[1])
    pubmed_id = int(line[2])
    
    if not gene_id in gene_id_to_pubmed_id:
        gene_id_to_pubmed_id[gene_id] = {}
    gene_id_to_pubmed_id[gene_id][pubmed_id] = None

    unique_pubmed_ids[pubmed_id] = None
    
f.close()


#pp.pprint(gene_id_to_pubmed_id)
#pp.pprint(unique_pubmed_ids)


#
# connect to Neo4j
#
driver = GraphDatabase.driver(uri, auth=(username, password))

#
# clear the way (CRUDE)
#
cmd = 'MATCH (c:NCBI_PUBMED)-[r]-() DELETE r;'
with driver.session() as session:
    session.run(cmd)
cmd = 'MATCH (c:NCBI_PUBMED) DELETE c;'
with driver.session() as session:
    session.run(cmd)

#
# load pubmed
#
pubmed_list = []
for pm in unique_pubmed_ids.keys():
    pubmed_list.append([pm])
cmd = 'UNWIND $list_to_use AS n CREATE (p:NCBI_PUBMED {id : n[0]}) RETURN p;'
ut.load_list(pubmed_list, chunk_size, driver, cmd)

#
# Make index on id
#
cmd = 'CREATE INDEX ON :NCBI_PUBMED(id);'
with driver.session() as session:
    session.run(cmd)

#
# load relationships
#
the_list = []
for gene_id in gene_id_to_pubmed_id.keys():
    for pubmed_id in gene_id_to_pubmed_id[gene_id].keys():
        the_list.append([gene_id, pubmed_id])
cmd = 'UNWIND $list_to_use AS n MATCH (g:NCBI_GENE), (p:NCBI_PUBMED) WHERE g.id = n[0] AND p.id = n[1] CREATE (p)-[r:INVOLVES_NCBI_GENE]->(g) RETURN p, r, g;'
ut.load_list(the_list, chunk_size, driver, cmd)




#
# close Neo4j driver
#
driver.close()
