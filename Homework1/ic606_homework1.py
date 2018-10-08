from math import log2
from datetime import datetime

starttime = datetime.now()

with open("./config.txt", "r") as config_file:
    cache_size = int(config_file.readline())
    ways = int(config_file.readline())
    block_size = int(config_file.readline())


"""
USER INPUT
policy: int. Eviction Policy. 0 for LRU, 1 for pseudo-LRU
benchmark: int. Benchmark selection: 0 for ping_trace,
           1:perlbench, 2:soplex, 3:povary, 4:libquantum, 5:astar, 6:xalancbmk (inside HW1_6_workloads folder)
debug_mode: boolean. False for default. set to True to see procedure, execution time, etc.
"""
policy = 0
benchmark = 0
debug_mode = True
"""
DO NOT MAKE CHANGES BELOW THIS COMMENT.
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


# 1 word: 8byte
num_sets = int(cache_size * 1024 / (block_size * ways))
block_bit = int(log2(block_size / 8))
set_bit = int(log2(num_sets))
tag_bit = 64 - (block_bit + set_bit)
byte_offset = 3


# Counters
count_total = 0
count_read = 0
count_write = 0
miss_read = 0
miss_write = 0
evict_clean = 0
evict_dirty = 0
checksum = 0

# cache[set][way] = {"Valid": int(0 or 1), "Dirty": int(0 or 1), "Tag": int, "Data": str(empty)}
cache = [[{"Valid": 0, "Dirty": 0, "Tag": -1, "Data": ""} for i in range(ways)] for j in range(num_sets)]
LRU = [[] for i in range(num_sets)]
#pLRU = [[-1, -1] for i in range(num_sets)]


def get_victim(set_index):
    if policy == 0:
        victim_way = LRU[set_index].pop(0)
    elif policy == 1:
        pass
    return victim_way


def update_policy(set_index, used_way):
    if policy == 0:
        if used_way in LRU[set_index]:
            LRU[set_index].append(LRU[set_index].pop(LRU[set_index].index(used_way)))
        else:
            LRU[set_index].append(used_way)
    elif policy == 1:
        pass


def get_index_tag(address):
    set_index = (address >> (block_bit + byte_offset)) - ((address >> (block_bit + byte_offset + set_bit)) << set_bit)
    tag = address >> (block_bit + byte_offset + set_bit)
    return set_index, tag


def evict(set_index):
    global evict_dirty, evict_clean
    victim_way = get_victim(set_index)
    if cache[set_index][victim_way]["Dirty"]:
        evict_dirty += 1
    else:
        evict_clean += 1

    cache[set_index][victim_way] = {"Valid": 0, "Dirty": 0, "Tag": -1, "Data": ""}
    return victim_way


def get_empty_way(set_index):
    one_set = [x["Valid"] for x in cache[set_index]]
    return one_set.index(0) if 0 in one_set else -1


def is_hit(address):
    set_index, tag = get_index_tag(address)
    one_set = [x["Tag"] for x in cache[set_index]]
    return one_set.index(tag) if tag in one_set else -1


def fetch_data(address):
    index, tag = get_index_tag(address)
    way = get_empty_way(index)
    if way == -1:
        evict(index)
        way = get_empty_way(index)
    cache[index][way]["Valid"] = 1
    cache[index][way]["Tag"] = tag
    update_policy(index, way)
    return index, way


def set_data(set_index, way):
    cache[set_index][way]["Dirty"] = 1
    update_policy(index, way)


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
                fetch_data(address)
        elif rw == "W":
            count_write += 1
            if not way == -1:
                set_data(index, way)
            else:
                miss_write += 1
                t1, t2 = fetch_data(address)
                set_data(t1, t2)
        if debug_mode and count_total % 1000000 == 0:
            print(count_total)


for x in range(num_sets):
    for y in range(ways):
        oneblock = cache[x][y]
        if oneblock["Valid"] == 1:
            checksum = checksum ^ (((oneblock["Tag"]^x) << 1) | oneblock["Dirty"])
checksum_hex = hex(checksum)

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
    resultio.write("Read miss rate: {}%\n".format(miss_read/count_read*100))
    resultio.write("Write miss rate: {}%\n".format(miss_write/count_write*100))
    resultio.write("Clean evictions: {}\n".format(evict_clean))
    resultio.write("Dirty evictions: {}\n".format(evict_dirty))
    resultio.write("Checksum: {}\n".format(checksum_hex))

if debug_mode:
    endtime = datetime.now()
    print("Elapsed time:", endtime - starttime)

"""
-- General Stats --
Capacity: 16
Way: 4
Block size: 16
Total accesses: 66974
Read accesses: 52362
Write accesses: 14612
Read misses: 8713
Write misses: 1981
Read miss rate: 16.63992972002597%
Write miss rate: 13.55735012318642%
Clean evictions: 7703
Dirty evictions: 1967
Checksum: 0x1152c43a
"""