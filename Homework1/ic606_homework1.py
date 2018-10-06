from math import log2

with open("./config.txt", "r") as config_file:
    cache_size = int(config_file.readline())
    ways = int(config_file.readline())
    block_size = int(config_file.readline())


"""
USER INPUT
policy: int. Eviction Policy. 0 for LRU, 1 for pseudo-LRU
benchmark: int. Benchmark selection: 0 for ping_trace,
           1:perlbench, 2:soplex, 3:povary, 4:libquantum, 5:astar, 6:xalancbmk (inside HW1_6_workloads)
"""
policy = 0
benchmark = 0

"""
DO NOT MAKE CHANGES BELOW THIS COMMENT.
"""


# 1 word: 8byte
num_sets = int(cache_size * 1024 / (block_size * ways))
block_bit = int(log2(block_size / 8))
set_bit = int(log2(num_sets))
tag_bit = 64 - (block_bit + set_bit)
byte_offset = 3


benchname = ["ping", "perlbench", "soplex", "povary", "libquantum", "astar", "xalancbmk"]
benchlist = ["./ping_trace.out",
             "./HW1_6_workloads/400_perlbench.out",
             "./HW1_6_workloads/450_soplex.out",
             "./HW1_6_workloads/453_povray.out",
             "./HW1_6_workloads/462_libquantum.out",
             "./HW1_6_workloads/473_astar.out",
             "./HW1_6_workloads/483_xalancbmk.out"]

# Counters
count_total = 0
count_read = 0
count_write = 0
miss_read = 0
miss_write = 0
evict_clean = 0
evict_dirty = 0

# cache[set][way] = {"Valid": int(0 or 1), "Dirty": int(0 or 1), "Tag": int, "Data": str(empty)}
cache = [[{"Valid": 0, "Dirty": 0, "Tag": -1, "Data": ""} for i in range(ways)] for j in range(num_sets)]
LRU = [[-1] * ways for i in range(num_sets)]
#pLRU = [[-1, -1] for i in range(num_sets)]


def getIndexTag(address):
    cache_index = (address >> (block_bit + byte_offset)) - ((address >> (block_bit + byte_offset + set_bit)) << set_bit)
    cache_tag = address >> (block_bit + byte_offset + set_bit)
    return cache_index, cache_tag


def evict(cache_index, policy_num):
    global evict_dirty, evict_clean
    if policy_num == 0:
        cacheSet = LRU[cache_index]
        cache_way = cacheSet.index(min(cacheSet))
        if cache[cache_index][cache_way]["Dirty"]:
            evict_dirty += 1
        else:
            evict_clean += 1
        LRU[cache_index][cache_way] = -1
    elif policy_num == 1:
        pass
    cache[cache_index][cache_way] = {"Valid": 0, "Dirty": 0, "Tag": -1, "Data": ""}
    return cache_way


def getEmptyWay(cache_index):
    cacheSet = [x["Valid"] for x in cache[cache_index]]
    return cacheSet.index(0) if 0 in cacheSet else -1


def isHit(address):
    cache_index, tag = getIndexTag(address)
    cacheSet = [x["Tag"] for x in cache[cache_index]]
    return cacheSet.index(tag) if tag in cacheSet else -1


def fetchData(address, counter):
    index, tag = getIndexTag(address)
    cacheWay = getEmptyWay(index)
    if cacheWay == -1:
        evict(index, policy)
        cacheWay = getEmptyWay(index)
    cache[index][cacheWay]["Valid"] = 1
    cache[index][cacheWay]["Tag"] = tag
    LRU[index][cacheWay] = counter
    return index, cacheWay


def setData(cacheSet, cacheWay, counter):
    cache[cacheSet][cacheWay]["Dirty"] = 1
    LRU[index][cacheWay] = counter


with open(benchlist[benchmark], "r") as memoryio:
    for line in memoryio:
        count_total += 1
        rw, address = line.strip().split()
        address = int(address, 0)
        index, tag = getIndexTag(address)
        way = isHit(address)
        if rw == "R":
            count_read += 1
            if not way == -1:
                LRU[index][way] = count_total
            else:
                miss_read += 1
                fetchData(address, count_total)
        elif rw == "W":
            count_write += 1
            if not way == -1:
                setData(index, way, count_total)
            else:
                miss_write += 1
                t1, t2 = fetchData(address, count_total)
                setData(t1, t2, count_total)


file_name = "{}_{}_{}_{}.out".format(benchlist[benchmark], cache_size, ways, block_size)
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

"""
-- General Stats--
Capacity: 16
Way: 4
Block size: 16
Total accesses: 66974
Read accesses: 52362
Write accesses: 14612
Read misses: 8713
Write misses: 1981
Read miss rate: 16.64%
Write miss rate: 13.56%
Clean evictions: 7703
Dirty evictions: 1967
"""