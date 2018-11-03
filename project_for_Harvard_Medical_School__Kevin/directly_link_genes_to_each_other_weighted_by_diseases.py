#
# useful libraries
#
import pprint as pp
from neo4j import GraphDatabase
import argparse
import sys
import os

#
# CRUDE
#
cwd = '/'.join(os.getcwd().split('/')[0:-1])
sys.path.append(cwd)
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
# get data
#
pairs = {}
cmd = 'MATCH (d:HMS_DISEASE)-[rdg1:INVOLVES_NCBI_GENE]->(g1:NCBI_GENE), (d)-[rdg2:INVOLVES_NCBI_GENE]->(g2:NCBI_GENE) WHERE g1.id <> g2.id RETURN d, g1, g2'
with driver.session() as session:
    results = session.run(cmd)
    for record in results:
        genes = '____'.join(sorted([record['g1']['symbol'], record['g2']['symbol']]))
        disease = record['d']['name']
        if not genes in pairs:
            pairs[genes] = {}
        pairs[genes][disease] = None

#
# prepare data
#
the_list = []
for genes in pairs:
    gene_list = genes.split('____')
    gene1 = gene_list[0]
    gene2 = gene_list[1]
    disease_count = len(pairs[genes].keys())

    the_list.append([gene1, gene2, disease_count])
    the_list.append([gene2, gene1, disease_count])

#
# load into database
#
cmd = 'MATCH ()-[r:SHARE_ONE_OR_MORE_HMS_DISEASES]-() DELETE r;'
with driver.session() as session:
    session.run(cmd)

cmd = 'UNWIND $list_to_use AS n MATCH (ga:NCBI_GENE), (gb:NCBI_GENE) WHERE ga.symbol = n[0] AND gb.symbol = n[1] CREATE (ga)-[r:SHARE_ONE_OR_MORE_HMS_DISEASES {disease_count : n[2]}]->(gb);'
ut.load_list(the_list, chunk_size, driver, cmd)
    
