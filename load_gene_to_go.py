#
# Copyright 2018 Whole-Systems Enterprises, Inc.
#

#
# import useful libraries
#
from neo4j import GraphDatabase
import pprint as pp
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

chunk_size = args.chunk_size

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
# connect to Neo4j
#
driver = GraphDatabase.driver(uri, auth=(username, password))

#
# read the file
#
go_id_to_term = {}
go_id_to_category = {}
go_id_to_gene = {}
unique_category = {}
f = open('data/gene/gene2go')
for line in f:
    line = [x.strip() for x in line.split('\t')]

    tax_id = line[0]
    if tax_id == '#tax_id':  continue
    tax_id = int(tax_id)

    if limit_taxonomies:
        if not tax_id in tax_ids_to_keep:
            continue
    
    gene_id = int(line[1])
    go_id = line[2]
    term = line[5]

    pubmed = line[6]
    if pubmed.strip() == '-':
        pubmed = None
    else:
        pubmed = [int(x) for x in pubmed.split('|')]

    category = line[7]

    go_id_to_term[go_id] = term
    go_id_to_category[go_id] = category

    if not go_id in go_id_to_gene:
        go_id_to_gene[go_id] = {}
    go_id_to_gene[go_id][gene_id] = None

    unique_category[category] = None
    
f.close()

#
# load go categories
#
cmd = 'MATCH (c:GENE_ONTOLOGY_CATEGORY)-[r]-() DELETE r;'
with driver.session() as session:
    session.run(cmd)
cmd = 'MATCH (c:GENE_ONTOLOGY_CATEGORY) DELETE c;'
with driver.session() as session:
    session.run(cmd)

the_list = []
for cat in unique_category.keys():
    the_list.append([cat])
cmd = 'UNWIND $list_to_use AS n CREATE (c:GENE_ONTOLOGY_CATEGORY {name : n[0]}) RETURN c;'
ut.load_list(the_list, chunk_size, driver, cmd)

cmd = 'CREATE INDEX ON :GENE_ONTOLOGY_CATEGORY(name);'
with driver.session() as session:
    session.run(cmd)

#
# load the rest
#
go_list = []
go_cat_list = []
go_gene_list = []
for go_id in go_id_to_term.keys():
    term = go_id_to_term[go_id]
    cat = go_id_to_category[go_id]
    go_list.append([go_id, term])
    go_cat_list.append([go_id, cat])

    for gene_id in go_id_to_gene[go_id].keys():
        go_gene_list.append([go_id, gene_id])

cmd = 'MATCH (c:GENE_ONTOLOGY)-[r]-() DELETE r;'
with driver.session() as session:
    session.run(cmd)
cmd = 'MATCH (c:GENE_ONTOLOGY) DELETE c;'
with driver.session() as session:
    session.run(cmd)
cmd = 'UNWIND $list_to_use AS n CREATE (c:GENE_ONTOLOGY {id : n[0], term : n[1]}) RETURN c;'
ut.load_list(go_list, chunk_size, driver, cmd)
cmd = 'CREATE INDEX ON :GENE_ONTOLOGY(id);'
with driver.session() as session:
    session.run(cmd)

cmd = 'UNWIND $list_to_use AS n MATCH (cat:GENE_ONTOLOGY_CATEGORY), (go:GENE_ONTOLOGY) WHERE go.id = n[0] AND cat.name = n[1] CREATE (go)-[r:HAS_GENE_ONTOLOGY_CATEGORY]->(cat) RETURN go, cat, r;'
ut.load_list(go_cat_list, chunk_size, driver, cmd)
cmd = 'UNWIND $list_to_use AS n MATCH (g:NCBI_GENE), (go:GENE_ONTOLOGY) WHERE go.id = n[0] AND g.id = n[1] CREATE (g)-[r:HAS_GENE_ONTOLOGY]->(go) RETURN go, g, r;'
ut.load_list(go_gene_list, chunk_size, driver, cmd)


#
# close Neo4j driver
#
driver.close()



