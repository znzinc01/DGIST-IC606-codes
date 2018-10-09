from math import log2
from datetime import datetime
"""
USER INPUT
policy: int. Eviction Policy. 0 for LRU, 1 for pseudo-LRU
benchmark: int. Benchmark selection: 0 for ping_trace,
           1:perlbench, 2:soplex, 3:povary, 4:libquantum, 5:astar, 6:xalancbmk (inside HW1_6_workloads folder)
debug_mode: boolean. False for default. set to True to see procedure and execution time.
"""
policy = 1
benchmark = 1
debug_mode = False
"""
THERE IS NO OPTIONAL VARIABLE BELOW THIS COMMENT.
"""
policy_name = ["LRU", "pseudoLRU"]
bench_name = ["ping_trace", "perlbench", "soplex", "povary", "libquantum", "astar", "xalancbmk"]
bench_list = ["./ping_trace.out",
              "./HW1_6_workloads/400_perlbench.out",
              "./HW1_6_workloads/450_soplex.out",
              "./HW1_6_workloads/453_povray.out",
              "./HW1_6_workloads/462_libquantum.out",
              "./HW1_6_workloads/473_astar.out",
              "./HW1_6_workloads/483_xalancbmk.out"]

start_time = datetime.now()

with open("./config.txt", "r") as config_file:
    cache_size = int(config_file.readline())
    ways = int(config_file.readline())
    way_bin_digits = int(log2(ways))
    block_size = int(config_file.readline())

# 1 word: 8byte
num_sets = int(cache_size * 1024 / (block_size * ways))
block_bit = int(log2(block_size / 8))
set_bit = int(log2(num_sets))
tag_bit = 64 - (block_bit + set_bit)
byte_offset = 3

# Counters
count_total, count_read, count_write = 0, 0, 0
miss_read, miss_write = 0, 0
evict_clean, evict_dirty = 0, 0
checksum = 0

# cache[set][way] = {"Valid": int(0 or 1), "Dirty": int(0 or 1), "Tag": int, "Data": str(empty)}
cache = [[{"Valid": 0, "Dirty": 0, "Tag": -1, "Data": ""} for i in range(ways)] for j in range(num_sets)]
LRU = [[] for i in range(num_sets)]
pLRU = [[0 for i in range(ways - 1)]for j in range(num_sets)]


# Functions defined for modeling cache.
def get_victim(set_index):
    """
    Selects the victim way based on each policy. policy is declared at the front of this code as a global variable.
    :param set_index: int. The index of set to chose victim.
    :return victim_way: int. The index of way to be evicted.
    """
    if policy == 0:
        victim_way = LRU[set_index].pop(0)
    elif policy == 1:
        victim_way = 0
        next_tree = 0
        for i in range(way_bin_digits):
            x = (way_bin_digits - 1) - i
            victim_way += pLRU[set_index][next_tree] * (2 ** x)
            next_tree += (2 ** (i + 1)) - 1 + (victim_way >> x)
    return victim_way


def update_policy(set_index, used_way):
    """
    Updates the state of usage based on each policy. sets used_way as MRU.
    :param set_index: int. The index of set to update.
    :param used_way: int. The index of way to set as MRU.
    :return: Returns Nothing.
    """
    if policy == 0:
        if used_way in LRU[set_index]:
            LRU[set_index].append(LRU[set_index].pop(LRU[set_index].index(used_way)))
        else:
            LRU[set_index].append(used_way)
    elif policy == 1:
        next_tree = 0
        for i in range(way_bin_digits):
            x = (way_bin_digits - 1) - i
            current_bin_digit = int(used_way / (2 ** x)) % 2
            if pLRU[set_index][next_tree] == current_bin_digit:
                pLRU[set_index][next_tree] = (pLRU[set_index][next_tree] + 1) % 2
            next_tree += (2 ** (i + 1)) + used_way >> x


def get_index_tag(address):
    """
    Parses the address into index and tag.
    :param address: int. Address in decimal int.
    :return: tuple of int. Consisted of index and tag.
    """
    set_index = (address >> (block_bit + byte_offset)) - ((address >> (block_bit + byte_offset + set_bit)) << set_bit)
    tag = address >> (block_bit + byte_offset + set_bit)
    return set_index, tag


def evict(set_index):
    """
    Evicts a single cache block based on each policy.
    :param set_index: The index of set that needs one empty block, but currently full.
    :return: int. the way that has been evicted.
    """
    global evict_dirty, evict_clean
    victim_way = get_victim(set_index)
    if cache[set_index][victim_way]["Dirty"]:
        evict_dirty += 1
    else:
        evict_clean += 1

    cache[set_index][victim_way] = {"Valid": 0, "Dirty": 0, "Tag": -1, "Data": ""}
    return victim_way


def get_empty_way(set_index):
    """
    Get an index of empty way. if there's multiple, the smallest index will be returned.
    :param set_index: The index of set that are going to be searched.
    :return: int. Index of empty way.
    """
    one_set = [x["Valid"] for x in cache[set_index]]
    return one_set.index(0) if 0 in one_set else -1


def is_hit(address):
    """
    Check whether that data of given address is on(hit) the cache.
    :param address: int. Address in decimal int.
    :return: int. Index of way that contains data of given address.
    """
    set_index, tag = get_index_tag(address)
    one_set = [x["Tag"] for x in cache[set_index]]
    return one_set.index(tag) if tag in one_set else -1


def fetch_data(index, tag):
    """
    Fetches data from storage to cache. (No actual data is set since this homework requires no data I/O)
    :param index: int. The set index of parsed address.
    :param tag: int. The tag of parsed address.
    :return: int. Index of way that contains the fetched data.
    """
    way = get_empty_way(index)
    if way == -1:
        way = evict(index)
    cache[index][way]["Valid"] = 1
    cache[index][way]["Tag"] = tag
    update_policy(index, way)
    return way


def set_data(set_index, way):
    """
    Write data to cache, and set the dirty bit as 1. (No actual data is set since this homework requires no data I/O)
    :param set_index: int. The set index of parsed address.
    :param way: int. The way of cache which needs to be written.
    :return: Returns nothing.
    """
    cache[set_index][way]["Dirty"] = 1
    update_policy(set_index, way)


# Read Data and compute
with open(bench_list[benchmark], "r") as memoryio:
    for line in memoryio:
        count_total += 1
        rw, address = line.strip().split()
        address = int(address, 0)
        index, tag = get_index_tag(address)
        way = is_hit(address)
        if rw == "R":
            count_read += 1
            if not way == -1:
                update_policy(index, way)
            else:
                miss_read += 1
                fetch_data(index, tag)
        elif rw == "W":
            count_write += 1
            if not way == -1:
                set_data(index, way)
            else:
                miss_write += 1
                set_data(index, fetch_data(index, tag))
        if debug_mode and count_total % 1000000 == 0:
            print(count_total)

# Calculate Checksum
for x in range(num_sets):
    for y in range(ways):
        oneblock = cache[x][y]
        if oneblock["Valid"] == 1:
            checksum = checksum ^ (((oneblock["Tag"] ^ x) << 1) | oneblock["Dirty"])
checksum_hex = hex(checksum)  # Becomes string starting with "0x"

# Write to .out file
# To distinguish between LRU and pseudo-LRU, policy name is specified at the end of file name
# (Which is not required from homework instruction)
file_name = "./{}_{}_{}_{}_{}.out".format(bench_name[benchmark],
                                          cache_size, ways, block_size, policy_name[policy])
with open(file_name, "w") as resultio:
    resultio.write("-- General Stats --\n")
    resultio.write("Capacity: {}\n".format(cache_size))
    resultio.write("Way: {}\n".format(ways))
    resultio.write("Block size: {}\n".format(block_size))
    resultio.write("Total accesses: {}\n".format(count_total))
    resultio.write("Read accesses: {}\n".format(count_read))
    resultio.write("Write accesses: {}\n".format(count_write))
    resultio.write("Read misses: {}\n".format(miss_read))
    resultio.write("Write misses: {}\n".format(miss_write))
    resultio.write("Read miss rate: {}%\n".format(miss_read/count_read * 100))
    resultio.write("Write miss rate: {}%\n".format(miss_write/count_write * 100))
    resultio.write("Clean evictions: {}\n".format(evict_clean))
    resultio.write("Dirty evictions: {}\n".format(evict_dirty))
    resultio.write("Checksum: {}\n".format(checksum_hex))

# If debug mode is on, print the elapsed time.
if debug_mode:
    end_time = datetime.now()
    print("Elapsed time:", end_time - start_time)
