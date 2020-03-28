#
# Copyright 2018 Whole-Systems Enterprises, Inc.
#

#
# import useful libraries
#
import pprint as pp
import pickle
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
args = parser.parse_args()

chunk_size = args.chunk_size

#
# user settings
#
output_directory = 'output'

load_all_synonyms = True
load_all_synonyms_to_tax_id = True
load_all_synonyms_to_gene_id = True

#
# Neo4j settings
#
username = args.username
password = args.password
uri = 'bolt://' + args.hostname + ':7687'

#
# connect to Neo4j
#
driver = GraphDatabase.driver(uri, auth=(username, password), encrypted=False)

#
# load our data structures
#
with open(output_directory + '/synonyms_to_gene_id.pickle', 'rb') as f:
    synonyms_to_gene_id = pickle.load(f)
with open(output_directory + '/synonyms_to_tax_id.pickle', 'rb') as f:
    synonyms_to_tax_id = pickle.load(f)

#########################
#   load all synonyms   #
#########################

if load_all_synonyms:

    #
    # clear the way (CRUDE)
    #
    cmd = 'MATCH (c:NCBI_GENE_SYNONYM)-[r]-() DELETE r;'
    with driver.session() as session:
        session.run(cmd)
    cmd = 'MATCH (c:NCBI_GENE_SYNONYM) DELETE c;'
    with driver.session() as session:
        session.run(cmd)
    
    #
    # make sure we know all the unique synonyms
    #
    all_synonyms = {}
    for syn in synonyms_to_gene_id.keys():
        all_synonyms[syn] = None
    for syn in synonyms_to_tax_id.keys():
        all_synonyms[syn] = None
    all_synonyms_list = []
    for syn in sorted(list(all_synonyms.keys())):
        all_synonyms_list.append([syn])

    #
    # report how many synonyms we are loading
    #
    print()
    print('We are loading ' + str(len(all_synonyms_list)) + ' gene synonym nodes.')
    print()

    #
    # load all synonyms
    #
    cmd = 'UNWIND $list_to_use AS n CREATE (c:NCBI_GENE_SYNONYM {symbol : n[0]}) RETURN c;'
    ut.load_list(all_synonyms_list, chunk_size, driver, cmd)

    #
    # create index on symbol
    #
    cmd = 'CREATE INDEX ON :NCBI_GENE_SYNONYM(symbol);'
    with driver.session() as session:
        session.run(cmd)



#####################################
#   link synonyms to taxonomy IDs   #
#####################################

if load_all_synonyms_to_tax_id:

    #
    # clear the way (CRUDE)
    #
    cmd = 'MATCH (c:NCBI_GENE_SYNONYM)-[r:HAS_NCBI_TAXONOMY]->(t:NCBI_TAXONOMY) DELETE r;'
    with driver.session() as session:
        session.run(cmd)
    
    #
    # organize list
    #
    link_list = []
    for syn in sorted(list(synonyms_to_tax_id.keys())):
        for tax_id in sorted(list(synonyms_to_tax_id[syn].keys())):
            link_list.append([syn, tax_id])

    #
    # report how many synonym to tax ID relationships we are loading
    #
    print()
    print('We are loading ' + str(len(link_list)) + ' gene synonym to taxonomy relationships.')
    print()

    #
    # load all synonym to tax ID links
    #
    cmd = 'UNWIND $list_to_use AS n MATCH (gs:NCBI_GENE_SYNONYM), (t:NCBI_TAXONOMY) WHERE gs.symbol = n[0] and t.id = n[1] CREATE (gs)-[r:HAS_NCBI_TAXONOMY]->(t) RETURN gs, r, t'
    ut.load_list(link_list, chunk_size, driver, cmd)

#################################
#   link synonyms to gene IDs   #
#################################

if load_all_synonyms_to_gene_id:

    #
    # clear the way (CRUDE)
    #
    cmd = 'MATCH (gs:NCBI_GENE_SYNONYM)<-[r:HAS_NCBI_GENE_SYNONYM]-(g:NCBI_GENE) DELETE r;'
    with driver.session() as session:
        session.run(cmd)
    
    #
    # organize list
    #
    gene_link_list = []
    for syn in sorted(list(synonyms_to_gene_id.keys())):
        for gene_id in sorted(list(synonyms_to_gene_id[syn].keys())):
            gene_link_list.append([syn, gene_id])

    #
    # report how many synonym to tax ID relationships we are loading
    #
    print()
    print('We are loading ' + str(len(gene_link_list)) + ' gene synonym to gene relationships.')
    print()

    #
    # load all synonym to tax ID links
    #
    cmd = 'UNWIND $list_to_use AS n MATCH (gs:NCBI_GENE_SYNONYM), (g:NCBI_GENE) WHERE gs.symbol = n[0] and g.id = n[1] CREATE (gs)<-[r:HAS_NCBI_GENE_SYNONYM]-(g) RETURN gs, r, g'
    ut.load_list(gene_link_list, chunk_size, driver, cmd)
   
#
# close Neo4j driver
#
driver.close()
