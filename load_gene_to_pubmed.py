#
# Copyright 2018 Whole-Systems Enterprises, Inc.
#

#
# import useful libraries
#
import pprint as pp
from neo4j import GraphDatabase
import sys
import argparse
import utilities as ut

#
# command line arguments
#
parser = argparse.ArgumentParser(description='Set up SageMaker training data.')
parser.add_argument('--hostname', type=str, help='Hostname.', required=True)
parser.add_argument('--username', type=str, help='Neo4j username.', required=True)
parser.add_argument('--password', type=str, help='Neo4j password.', required=True)
parser.add_argument('--chunk-size', type=int, help='Chunk size.', default=25000)
parser.add_argument('--limit-taxonomies-to', type=str, help='Comma-delimited, e.g. 9606,10090,10116')
args = parser.parse_args()

chunk_size = 10000

limit_taxonomies = False
tax_ids_to_keep = []
if args.limit_taxonomies_to != None:
    limit_taxonomies = True
    tax_ids_to_keep = [int(x.strip()) for x in args.limit_taxonomies_to.split(',')] 

#
# configure Neo4j connection
#
username = args.username
password = args.password
uri = 'bolt://' + args.hostname + ':7687'
    
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
    if limit_taxonomies:
        if not tax_id in tax_ids_to_keep:
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
