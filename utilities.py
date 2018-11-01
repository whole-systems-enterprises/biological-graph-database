
#
# split a list into chunks
#
def split_a_list_into_equal_sized_chunks(the_list, chunk_size):
    chunks = [the_list[x:x+chunk_size] for x in range(0, len(the_list), chunk_size)]
    return chunks

#
# Neo4j transaction functions
#
def add_entry(list_to_use, driver, cmd):
    with driver.session() as session:
        session.write_transaction(create_entry, list_to_use, cmd)
        
def create_entry(tx, list_to_use, cmd):
    tx.run(cmd, list_to_use=list_to_use)

def load_list(the_list, chunk_size, driver, cmd):
    chunks = split_a_list_into_equal_sized_chunks(the_list, chunk_size)
    number_loaded = 0
    print()
    for ch in chunks:
        add_entry(ch, driver, cmd)
        number_loaded += len(ch)
        print('Added ' + str(number_loaded) + ' entries.')
    print()

