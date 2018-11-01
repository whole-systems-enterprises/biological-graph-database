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

#
# Neo4j settings
#
username = args.username
password = args.password
uri = 'bolt://' + args.hostname + ':7687'

#
# connect to Neo4j
#
driver = GraphDatabase.driver(uri, auth=(username, password))

#
# load our data structures
#
with open(output_directory + '/gene_to_tax_id.pickle', 'rb') as f:
    gene_to_tax_id = pickle.load(f)

#
# clear the way (CRUDE)
#
cmd = 'MATCH (c:NCBI_GENE)-[r:HAS_NCBI_TAXONOMY]->(t:NCBI_TAXONOMY) DELETE r;'
with driver.session() as session:
    session.run(cmd)

#
# organize list
#
link_list = []
for g in sorted(list(gene_to_tax_id.keys())):
    for tax_id in sorted(list(gene_to_tax_id[g].keys())):
        link_list.append([g, tax_id])

#
# report how many gene to tax ID relationships we are loading
#
print()
print('We are loading ' + str(len(link_list)) + ' gene to taxonomy relationships.')
print()

#
# load all synonym to tax ID links
#
cmd = 'UNWIND $list_to_use AS n MATCH (g:NCBI_GENE), (t:NCBI_TAXONOMY) WHERE g.id = n[0] and t.id = n[1] CREATE (g)-[r:HAS_NCBI_TAXONOMY]->(t) RETURN g, r, t'
ut.load_list(link_list, chunk_size, driver, cmd)
   
#
# close Neo4j driver
#
driver.close()
