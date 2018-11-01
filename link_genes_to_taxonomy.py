#
# import useful libraries
#
import pprint as pp
import pickle
from neo4j import GraphDatabase
import sys
import utilities as ut

#
# user settings
#
output_directory = 'output'
chunk_size = 25000

username = 'neo4j'
hostname = sys.argv[1]
password = sys.argv[2]
uri = 'bolt://' + hostname + ':7687'

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
