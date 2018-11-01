#
# useful libraries
#
import numpy as np
import pandas as pd
import pprint as pp
from neo4j import GraphDatabase
import sys
import argparse
import os

#
# CRUDE
#
cwd = '/'.join(os.getcwd().split('/')[0:-1])
sys.path.append(cwd)
import utilities as ut

#
# user settings
#
number_of_papers_file = '../data/Harvard_Medical_School__Kevin/TestSetToTryGraphDatabase/NumberPapersPerCaGeneCombo-Table-1.csv'
locate_genes = True

throw_out = ['', 'LYNCH|GENE', 'multiple', 'MUTYH-Biallelic', 'MUTYH-Monoallelic', 'TGFBR1()6A']

#
# command line arguments
#
parser = argparse.ArgumentParser(description='Set up SageMaker training data.')
parser.add_argument('--hostname', type=str, help='Hostname.', required=True)
parser.add_argument('--username', type=str, help='Neo4j username.', required=True)
parser.add_argument('--password', type=str, help='Neo4j password.', required=True)
args = parser.parse_args()

#
# Neo4j settings
#
output_directory = 'output'
username = args.username
password = args.password
uri = 'bolt://' + args.hostname + ':7687'

#
# load data
#
df = pd.read_csv(number_of_papers_file)

#
# remove duplicate entries (based on disease capitalization, presense of whitespace)
#
data = {}
unique_diseases = {}
for gene_set, disease, count in zip(df['Gene'], df['BetterName'], df['CountOfBetterName']):
    if str(gene_set).lower() == 'nan':
        gene_set = ''

    gene_set = gene_set.strip()
    disease = disease.strip()
    disease = disease.lower()
    unique_diseases[disease] = {}

    if not gene_set in data:
        data[gene_set] = {}
    if not disease in data[gene_set]:
        data[gene_set][disease] = 0
    data[gene_set][disease] += count


#
# clean up gene set entries
#
cleaned_data = {}
unique_gene_symbols = {}
for gene_set in data.keys():

    if gene_set.strip() in throw_out:
        continue

    new_gene_set = gene_set.replace(' ', '|')
    new_gene_set = new_gene_set.replace(',', '|')
    new_gene_set = new_gene_set.replace('+', '|')
    new_gene_set = new_gene_set.replace('&', '|')
    new_gene_set = new_gene_set.replace('-', '|')
    new_gene_set = new_gene_set.replace('*', '')

    if new_gene_set == 'RAD51B|C|D':
        new_gene_set = 'RAD51B|RAD51C|RAD51D'

    new_gene_set_as_list = [x.strip() for x in new_gene_set.split('|') if x.strip() not in throw_out]
    new_gene_set_as_list = sorted(new_gene_set_as_list)
    if len(new_gene_set_as_list) == 0:
        continue

    for g in new_gene_set_as_list:
        unique_gene_symbols[g] = None

    key = ', '.join(new_gene_set_as_list)

    if not key in cleaned_data:
        cleaned_data[key] = {'diseases' : {}}
    for disease in data[gene_set].keys():
        if not disease in cleaned_data[key]['diseases']:
            cleaned_data[key]['diseases'][disease] = 0
        cleaned_data[key]['diseases'][disease] += data[gene_set][disease]

#
# connect to Neo4j
#
driver = GraphDatabase.driver(uri, auth=(username, password))

#####################
#   load diseases   #
#####################

#
# clear the way (CRUDE)
#
cmd = 'MATCH (c:HMS_DISEASE)-[r]-() DELETE r;'
with driver.session() as session:
    session.run(cmd)
cmd = 'MATCH (c:HMS_DISEASE) DELETE c;'
with driver.session() as session:
    session.run(cmd)

#
# reorganize disease names for bulk load
#
disease_list = []
for disease in sorted(list(unique_diseases.keys())):
    disease_list.append([disease])

#
# load
#
cmd = 'UNWIND $list_to_use AS n CREATE (d:HMS_DISEASE {name : n[0]}) RETURN d;'
ut.load_list(disease_list, 1000, driver, cmd)

#
# Make indices on name
#
cmd = 'CREATE INDEX ON :HMS_DISEASE(name);'
with driver.session() as session:
    session.run(cmd)

    
########################
#   Locate the genes   #
########################

if locate_genes:
    cmd = 'MATCH (t:NCBI_TAXONOMY)<-[r:HAS_NCBI_TAXONOMY]-(g:NCBI_GENE) WHERE t.id = 9606 AND g.symbol = $symbol RETURN g.id;'
    for symbol in unique_gene_symbols.keys():
        with driver.session() as session:
            results = session.run(cmd, symbol = symbol)
            for record in results:
                unique_gene_symbols[symbol] = record['g.id']

    cmd = 'MATCH (t:NCBI_TAXONOMY)<-[r:HAS_NCBI_TAXONOMY]-(gs:NCBI_GENE_SYNONYM)<-[rgs:HAS_NCBI_GENE_SYNONYM]-(g:NCBI_GENE)-[gt:HAS_NCBI_TAXONOMY]->(t:NCBI_TAXONOMY) WHERE t.id = 9606 AND gs.symbol = $synonym RETURN g.id, g.symbol;'

    synonyms = {}
    for symbol in unique_gene_symbols.keys():
        if unique_gene_symbols[symbol] == None:
            synonyms[symbol] = []
            with driver.session() as session:
                results = session.run(cmd, synonym = symbol)
                for record in results:
                    synonyms[symbol].append((record['g.id'], record['g.symbol']))
    for syn in synonyms.keys():
        if len(synonyms[syn]) == 1:
            unique_gene_symbols[ synonyms[syn][0][1] ] = synonyms[syn][0][0]
            unique_gene_symbols[ syn ] = synonyms[syn][0][0]
        else:
            del(unique_gene_symbols[syn])


to_remove = []            
for gene_group in cleaned_data.keys():
    symbol_list = gene_group.split(', ')
    id_list = []
    for symbol in symbol_list:
        if symbol in unique_gene_symbols:
            id_list.append(unique_gene_symbols[symbol])
    if len(id_list) != len(symbol_list):
        to_remove.append(gene_group)
    else:
        cleaned_data[gene_group]['gene_ids'] = id_list

for r in to_remove:
    del(cleaned_data[r])
        
################################
#   finish loading everything  #
################################

#
# clear the way (CRUDE)
#
cmd = 'MATCH (c:HMS_GENE_COMBO)-[r]-() DELETE r;'
with driver.session() as session:
    session.run(cmd)
cmd = 'MATCH (c:HMS_GENE_COMBO) DELETE c;'
with driver.session() as session:
    session.run(cmd)
cmd = 'MATCH ()-[r:HAS_HMS_DISEASE]-() DELETE r;'
with driver.session() as session:
    session.run(cmd)

cmd_gene_combo = 'CREATE (gc:HMS_GENE_COMBO {name : $name}) RETURN gc;'    
cmd_gc_disease = 'MATCH (gc:HMS_GENE_COMBO), (d:HMS_DISEASE) WHERE gc.name = $gc_name AND d.name = $disease_name CREATE (gc)-[r:HAS_HMS_DISEASE {count : $count}]->(d) RETURN gc, r, d;'

cmd_gc_gene = 'MATCH (gc:HMS_GENE_COMBO), (g:NCBI_GENE) WHERE gc.name = $gc_name AND g.id = $gene CREATE (gc)-[r:HAS_NCBI_GENE]->(g) RETURN gc, r, g;'

for gene_group in sorted(list(cleaned_data.keys())):
    with driver.session() as session:
        session.run(cmd_gene_combo, name=gene_group)

    for disease in cleaned_data[gene_group]['diseases'].keys():
        with driver.session() as session:
            session.run(cmd_gc_disease, gc_name=gene_group, disease_name = disease, count = cleaned_data[gene_group]['diseases'][disease])

    for gene in cleaned_data[gene_group]['gene_ids']:
        with driver.session() as session:
            session.run(cmd_gc_gene, gc_name=gene_group, gene = gene)
            
#
# close Neo4j driver
#
driver.close()
