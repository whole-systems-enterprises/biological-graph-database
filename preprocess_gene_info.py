
#
# import useful libraries
#
import pprint as pp
import pickle
import uuid
import os

#
# user settings
#
gene_info_file = 'data/gene/gene_info'
output_directory = 'output'
max_gene_info_list_size = 1000000
tax_id_to_keep = [9606]

#
# CRUDELY clear the way
#
os.system('rm ' + output_directory + '/gene_lists/*')

#
# initialize data structures
#
gene_to_tax_id = {}
synonyms_to_tax_id = {}
synonyms_to_gene_id = {}
gene_info_list = []

#
# iterate through each line in the gene_info file
#
f = open(gene_info_file)
for line in f:
    line = [x.strip() for x in line.split('\t')]

    tax_id = line[0]

    if tax_id == '#tax_id':
        continue

    tax_id = int(tax_id)
    gene_id = int(line[1])
    symbol = line[2]
    synonyms = line[4]
    type_of_gene = line[9]
    name = line[11]

    if not tax_id in tax_id_to_keep:
        continue
    
    if symbol == '-':
        symbol = None
    if type_of_gene == '-':
        type_of_gene = None
    if name == '-':
        name = None

    cleaned_synonyms = [x for x in synonyms.split('|') if x != '-']
    for syn in cleaned_synonyms:
        if not syn in synonyms_to_tax_id:
            synonyms_to_tax_id[syn] = {}
        synonyms_to_tax_id[syn][tax_id] = None
        if not syn in synonyms_to_gene_id:
            synonyms_to_gene_id[syn] = {}
        synonyms_to_gene_id[syn][gene_id] = None
        
    if not gene_id in gene_to_tax_id:
        gene_to_tax_id[gene_id] = {}
    gene_to_tax_id[gene_id][tax_id] = None

    gene_info_list.append([gene_id, symbol, type_of_gene, name])
    if len(gene_info_list) >= max_gene_info_list_size:
        with open(output_directory + '/gene_lists/' + str(uuid.uuid4()) + '.pickle', 'wb') as f:
            pickle.dump(gene_info_list, f)
        gene_info_list = []
    
f.close()

#
# save our remaining gene list
#
with open(output_directory + '/gene_lists/' + str(uuid.uuid4()) + '.pickle', 'wb') as f:
    pickle.dump(gene_info_list, f)

#
# save our newly loaded data structures
#
with open(output_directory + '/gene_to_tax_id.pickle', 'wb') as f:
    pickle.dump(gene_to_tax_id, f)
with open(output_directory + '/synonyms_to_tax_id.pickle', 'wb') as f:
    pickle.dump(synonyms_to_tax_id, f)
with open(output_directory + '/synonyms_to_gene_id.pickle', 'wb') as f:
    pickle.dump(synonyms_to_gene_id, f)

