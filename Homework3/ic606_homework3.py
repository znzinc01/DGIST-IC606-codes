from math import log2


class CacheHW3():
    def __init__(self, cache_size, ways, block_size, policy_number, bus):
        self.cache_size = cache_size
        self.ways = ways
        self.block_size = block_size
        self.replacement_policy = policy_number
        self.master_bus = bus

        self.way_bin_digits = int(log2(self.ways))
        self.num_sets = int(self.cache_size * 1024 / (self.block_size * self.ways))
        self.block_bit = int(log2(self.block_size / 8))
        self.set_bit = int(log2(self.num_sets))
        self.tag_bit = 64 - (self.block_bit + self.set_bit)
        self.byte_offset = 3

        # Counters
        self.count_total, self.count_read, self.count_write = 0, 0, 0
        self.miss_read, self.miss_write = 0, 0
        self.evict_clean, self.evict_dirty = 0, 0

        # cache[set][way] = {"Valid": int(0 or 1), "Dirty": int(0 or 1), "Tag": int, "Data": str(empty)}
        self.cache = [[{"Valid": 0, "Dirty": 0, "Tag": -1, "Data": ""} for i in range(ways)]
                      for j in range(self.num_sets)]
        if self.replacement_policy == 0:
            self.LRU = [[] for i in range(self.num_sets)]
        elif self.replacement_policy == 1:
            self.pLRU = [[0 for i in range(ways - 1)] for j in range(self.num_sets)]

    # Functions defined for modeling cache.
    def get_victim(self, set_index):
        """
        Selects the victim way based on each policy. policy is declared at the front of this code as a global variable.
        :param set_index: int. The index of set to chose victim.
        :return victim_way: int. The index of way to be evicted.
        """
        if self.replacement_policy == 0:
            victim_way = self.LRU[set_index].pop(0)
        elif self.replacement_policy == 1:
            victim_way = 0
            next_tree = 0
            for i in range(self.way_bin_digits):
                x = (self.way_bin_digits - 1) - i
                victim_way += self.pLRU[set_index][next_tree] * (2 ** x)
                next_tree =ㅑ (2 ** (i + 1)) - 1 + (victim_way >> x)
        return victim_way

    def update_policy(self, set_index, used_way):
        """
        Updates the state of usage based on each policy. sets used_way as MRU.
        :param set_index: int. The index of set to update.
        :param used_way: int. The index of way to set as MRU.
        :return: Returns Nothing.
        """
        if self.replacement_policy == 0:
            if used_way in self.LRU[set_index]:
                self.LRU[set_index].append(self.LRU[set_index].pop(self.LRU[set_index].index(used_way)))
            else:
                self.LRU[set_index].append(used_way)
        elif self.replacement_policy == 1:
            next_tree = 0
            for i in range(self.way_bin_digits):
                x = (self.way_bin_digits - 1) - i
                current_bin_digit = int(used_way / (2 ** x)) % 2
                if self.pLRU[set_index][next_tree] == current_bin_digit:
                    self.pLRU[set_index][next_tree] = (self.pLRU[set_index][next_tree] + 1) % 2
                next_tree = (2 ** (i + 1)) - 1 + (used_way >> x)

    def get_index_tag(self, address):
        """
        Parses the address into index and tag.
        :param address: int. Address in decimal int.
        :return: tuple of int. Consisted of index and tag.
        """
        set_index = (address >> (self.block_bit + self.byte_offset)) - \
                    ((address >> (self.block_bit + self.byte_offset + self.set_bit)) << self.set_bit)
        tag = address >> (self.block_bit + self.byte_offset + self.set_bit)
        return set_index, tag

    def evict(self, set_index):
        """
        Evicts a single cache block based on each policy.
        :param set_index: The index of set that needs one empty block, but currently full.
        :return: int. the way that has been evicted.
        """
        victim_way = self.get_victim(set_index)
        if self.cache[set_index][victim_way]["Dirty"]:
            self.evict_dirty += 1
        else:
            self.evict_clean += 1

        self.cache[set_index][victim_way] = {"Valid": 0, "Dirty": 0, "Tag": -1, "Data": ""}
        return victim_way

    def get_empty_way(self, set_index):
        """
        Get an index of empty way. if there's multiple, the smallest index will be returned.
        :param set_index: The index of set that are going to be searched.
        :return: int. Index of empty way.
        """
        one_set = [x["Valid"] for x in self.cache[set_index]]
        return one_set.index(0) if 0 in one_set else -1

    def is_hit(self, address):
        """
        Check whether that data of given address is on(hit) the cache.
        :param address: int. Address in decimal int.
        :return: int. Index of way that contains data of given address.
        """
        set_index, tag = self.get_index_tag(address)
        one_set = [x["Tag"] for x in self.cache[set_index]]
        return one_set.index(tag) if tag in one_set else -1

    def fetch_data(self, index, tag):
        """
        Fetches data from storage to cache. (No actual data is set since this homework requires no data I/O)
        :param index: int. The set index of parsed address.
        :param tag: int. The tag of parsed address.
        :return: int. Index of way that contains the fetched data.
        """
        way = self.get_empty_way(index)
        if way == -1:
            way = self.evict(index)
        self.cache[index][way]["Valid"] = 1
        self.cache[index][way]["Tag"] = tag
        self.update_policy(index, way)
        return way

    def set_data(self, set_index, way):
        """
        Write data to cache, and set the dirty bit as 1. (No actual data is set since this homework requires no data I/O)
        :param set_index: int. The set index of parsed address.
        :param way: int. The way of cache which needs to be written.
        :return: Returns nothing.
        """
        self.cache[set_index][way]["Dirty"] = 1
        self.update_policy(set_index, way)

    def run_simulation(self, benchmark_number):
        with open(bench_list[benchmark_number], "r") as benchmark_file_obj:
            for line in benchmark_file_obj:
                self.count_total += 1
                rw, address = line.strip().split()
                address = int(address, 0)
                index, tag = self.get_index_tag(address)
                way = self.is_hit(address)
                if rw == "R":
                    self.count_read += 1
                    if not way == -1:
                        self.update_policy(index, way)
                    else:
                        self.miss_read += 1
                        self.fetch_data(index, tag)
                elif rw == "W":
                    self.count_write += 1
                    if not way == -1:
                        self.set_data(index, way)
                    else:
                        self.miss_write += 1
                        self.set_data(index, self.fetch_data(index, tag))

        checksum = 0
        for x in range(self.num_sets):
            for y in range(self.ways):
                oneblock = self.cache[x][y]
                if oneblock["Valid"] == 1:
                    checksum = checksum ^ (((oneblock["Tag"] ^ x) << 1) | oneblock["Dirty"])
        checksum_hex = hex(checksum)  # Becomes string starting with "0x"


class multicore_bus():
    def __init__(self, num_cores, protocol, capacity, associativity):
        pass

