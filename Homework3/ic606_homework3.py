from datetime import datetime
import sys
import os
from math import log2


class CacheHW3():
    def __init__(self, cache_size, ways, block_size,
                 cpu_num, total_cpus, protocol, bus, bus_queue, done_info):
        self.cache_size = cache_size
        self.ways = ways
        self.block_size = block_size
        self.replacement_policy = 0
        self.master_bus = bus
        self.master_queue = bus_queue
        self.master_done_info = done_info
        self.cpu_number = cpu_num
        self.cpu_total = total_cpus
        self.bus_duration = (total_cpus - 1) * 2 - 1
        self.protocol = protocol

        self.way_bin_digits = int(log2(self.ways))
        self.num_sets = int(self.cache_size * 1024 / (self.block_size * self.ways))
        self.block_bit = int(log2(self.block_size / 8))
        self.set_bit = int(log2(self.num_sets))
        self.tag_bit = 64 - (self.block_bit + self.set_bit)
        self.byte_offset = 3

        self.bus_action = []
        self.stall = False

        self.workload_file_name = "./HW3_workloads/core_{}_{}.out".format(cpu_num, total_cpus)
        self.workload_file = open(self.workload_file_name, "r")
        self.workload_file_end = False
        self.done = False

        # Counters
        self.count_cycle = 0
        self.count_read, self.count_write = 0, 0
        self.miss_read, self.miss_write = 0, 0

        # cache[set][way] = {"Valid": int(0 or 1), "Dirty": int(0 or 1), "Tag": int, "Data": str(empty)}
        self.cache = [[{"Valid": 0, "Dirty": 0, "Tag": -1, "Data": "", "Status": "I"} for i in range(ways)]
                      for j in range(self.num_sets)]
        self.LRU = [[] for i in range(self.num_sets)]

    def get_checksum(self):
        checksum = 0
        for x in range(self.num_sets):
            for y in range(self.ways):
                oneblock = self.cache[x][y]
                if oneblock["Status"] == "I":
                    status_hex = int("0x0b00", 16)
                elif oneblock["Status"] == "S":
                    status_hex = int("0x0b01", 16)
                elif oneblock["Status"] == "M":
                    status_hex = int("0x0b10", 16)
                elif oneblock["Status"] == "E":
                    status_hex = int("0x0b11", 16)
                checksum = checksum ^ ((oneblock["Tag"] << 2) | status_hex)
        return hex(checksum)  # Becomes string starting with "0x"

    def get_instruction(self):
        if not self.workload_file_end:
            one_line = self.workload_file.readline()
            if one_line:
                return one_line.split()
            else:
                self.workload_file_end = True
        return None, None

    def get_victim(self, set_index):
        victim_way = self.LRU[set_index][0]
        return victim_way

    def update_policy(self, set_index, used_way):
        if used_way in self.LRU[set_index]:
            self.LRU[set_index].append(self.LRU[set_index].pop(self.LRU[set_index].index(used_way)))
        else:
            self.LRU[set_index].append(used_way)

    def get_index_tag(self, address):
        set_index = (address >> (self.block_bit + self.byte_offset)) - \
                    ((address >> (self.block_bit + self.byte_offset + self.set_bit)) << self.set_bit)
        tag = address >> (self.block_bit + self.byte_offset + self.set_bit)
        return set_index, tag

    def evict(self, set_index, victim_way):
        self.LRU[set_index].pop(self.LRU[set_index].index(victim_way))
        self.cache[set_index][victim_way] = {"Valid": 0, "Dirty": 0, "Tag": -1, "Data": "", "Status": "I"}

    def get_empty_way(self, set_index):
        one_set = [x["Valid"] for x in self.cache[set_index]]
        return one_set.index(0) if 0 in one_set else -1

    def is_hit(self, address):
        set_index, tag = self.get_index_tag(address)
        one_set = [x["Tag"] for x in self.cache[set_index]]
        return one_set.index(tag) if tag in one_set else -1

    def get_index_way(self, address):
        set_index, tag = self.get_index_tag(address)
        one_set = [x["Tag"] for x in self.cache[set_index]]
        return set_index, one_set.index(tag) if tag in one_set else -1

    def fetch_data(self, index, tag):
        way = self.get_empty_way(index)
        if way == -1:
            way = self.get_victim(index)
            self.evict(index, way)
        self.cache[index][way]["Valid"] = 1
        self.cache[index][way]["Tag"] = tag
        self.cache[index][way]["Status"] = "S"
        self.update_policy(index, way)
        return way

    def set_data(self, set_index, way):
        self.cache[set_index][way]["Dirty"] = 1
        self.cache[set_index][way]["Status"] = "M"
        self.update_policy(set_index, way)

    def make_bus_request(self, address, act):
        # self.bus = []  # [cpu_number, target_address, bus_act,  cycles_left]
        self.bus_action = [self.cpu_number, address, act, self.bus_duration]
        if len(self.master_bus) == 0 and len(self.master_queue) == 0:
            self.master_bus.append(self.bus_action.copy())
        else:
            self.master_queue.append(self.cpu_number)
        self.stall = True

    def do_bus_request(self, address, act):
        set_index, tag = self.get_index_tag(address)
        way = self.is_hit(address)
        if way == -1:  # Invalid. For all bus requests, if current status is I, cache just ignores.
            return False
        # Action for bus request is same for MSI and MESI (Because no BusWB)
        if act == "BusRd":
            self.cache[set_index][way]["Status"] = "S"
        if act == "BusRFO" or act == "BusUp":
            self.evict(set_index, self.is_hit(address))
        return True

    def recieve_bus_response(self, address, cpu_number):
        if cpu_number == -1:
            index, way = self.get_index_way(address)
            self.cache[index][way]["Status"] = "E"

    def cache_action(self, rw, address):
        address = int(address, 0)
        index, tag = self.get_index_tag(address)
        way = self.is_hit(address)
        if rw == "R":
            self.count_read += 1
            if not way == -1:
                # Both MSI and MESI: when read hits, stay.
                self.update_policy(index, way)
            else:
                # MSI: fetch and set it as S. send BusRd.
                # MESI: fetch and set it as S for a moment. Send BusRd. If snoop misses, becomes E.
                self.miss_read += 1
                self.fetch_data(index, tag)
                self.cache[index][way]["Status"] = "S"
                self.make_bus_request(address, "BusRd")
        elif rw == "W":
            self.count_write += 1
            # Changing status is same except for E to M. MSI doesn't have E.
            if not way == -1:  # MSE
                status = self.cache[index][way]["Status"]
                if status == "S":
                    self.cache[index][way]["Status"] = "M"
                    self.make_bus_request(address, "BusUp")
                elif status == "M":
                    # No action for M - >M
                    pass
                elif status == "E":
                    self.cache[index][way]["Status"] = "M"
                    # No bus request for E -> M
                self.set_data(index, way)
            else:  # Invalid
                self.miss_write += 1
                new_way = self.fetch_data(index, tag)
                self.set_data(index, new_way)
                self.cache[index][new_way]["Status"] = "M"
                self.make_bus_request(address, "BusRFO")

    def print_stat(self, wfile=None):
        if wfile is None:
            print("-- Core {} --".format(self.cpu_number))
            print("Total accesses: {}".format(self.count_read + self.count_write))
            print("Total cycles: {}".format(self.count_cycle))
            print("IPC: {}".format((self.count_read + self.count_write) / self.count_cycle))
            print("Read accesses: {}".format(self.count_read))
            print("Write accesses: {}".format(self.count_write))
            print("Read misses: {}".format(self.miss_read))
            print("Write misses: {}".format(self.miss_write))
            print("Read miss rate : {}%".format(100 * self.miss_read / self.count_read))
            print("Write miss rate : {}%".format(100 * self.miss_write / self.count_write))
            print("Checksum: {}".format(self.get_checksum()))
        else:
            wfile.write("-- Core {} --\n".format(self.cpu_number))
            wfile.write("Total accesses: {}\n".format(self.count_read + self.count_write))
            wfile.write("Total cycles: {}\n".format(self.count_cycle))
            wfile.write("IPC: {}\n".format((self.count_read + self.count_write) / self.count_cycle))
            wfile.write("Read accesses: {}\n".format(self.count_read))
            wfile.write("Write accesses: {}\n".format(self.count_write))
            wfile.write("Read misses: {}\n".format(self.miss_read))
            wfile.write("Write misses: {}\n".format(self.miss_write))
            wfile.write("Read miss rate : {}%\n".format(100 * self.miss_read / self.count_read))
            wfile.write("Write miss rate : {}%\n".format(100 * self.miss_write / self.count_write))
            wfile.write("Checksum: {}\n".format(self.get_checksum()))
            

    def run(self):
        if not self.workload_file_end:
            self.count_cycle += 1
            if self.stall:
                if (not self.master_bus) and len(self.master_queue) == 0:
                    self.master_bus.append(self.bus_action.copy())
                elif (not self.master_bus) and self.master_queue[0] == self.cpu_number:
                    self.master_bus.append(self.bus_action.copy())
                    self.master_queue.pop(0)
            else:
                rw, address = self.get_instruction()
                if rw is None:
                    pass
                else:
                    self.cache_action(rw, address)
        else:
            self.master_done_info[self.cpu_number] = True


class MulticoreBus():
    def __init__(self, num_cores, protocol, capacity, associativity, debug):
        self.num_cores = num_cores  # 2, 4, 8
        self.protocol = protocol  # 0 for MSI, 1 for MESI
        self.capacity = capacity  # 64, 128, 256
        self.ways = associativity  # 4, 8
        self.block_size = 64  # 64Bit

        self.bus = []  # [cpu_number, target_address, bus_act,  cycles_left]
        self.bus_send_queue = []  # Stores the core number waiting for bus to be empty
        self.bus_recieve_queue = []  # Store the BusRd responds for each core.
        self.done_info = [False for i in range(num_cores)]

        self.debug = debug
        self.count = 0

        self.cores = []
        # (self, cache_size, ways, block_size, workload_fname, protocol, bus, bus_queue)
        for i in range(num_cores):
            # (self, cache_size, ways, block_size, cpu_num, total_cpus, protocol, bus, bus_queue)
            self.cores.append(CacheHW3(self.capacity, self.ways, self.block_size, i, num_cores,
                                       self.protocol, self.bus, self.bus_send_queue, self.done_info))

    def run_siumulation(self):
        if self.debug:
            print("Started at:", datetime.now())
        while True:
            self.count += 1
            if not (False in self.done_info):
                break
            for i in range(self.num_cores):
                self.cores[i].run()
            if self.bus:
                self.bus[0][3] -= 1
                if self.bus[0][3] < 0:
                    self.cores[self.bus[0][0]].stall = False
                    popped = self.bus.pop()
                    for i in range(self.num_cores):
                        if i != popped[0]:
                            self.bus_recieve_queue.append(self.cores[i].do_bus_request(popped[1], popped[2]))
                        else:
                            self.bus_recieve_queue.append(None)
                    if popped[2] == "BusRd" and self.protocol == 1:  # Only required at MESI
                        for i in range(self.num_cores):
                            if self.bus_recieve_queue[i] is True:
                                self.cores[popped[0]].recieve_bus_response(popped[1], i)
                                break
                        else:
                            self.cores[popped[0]].recieve_bus_response(popped[1], -1)

            if self.debug and self.count % 1000000 == 0:
                print("=========================================================")
                print("Count:", self.count, "/ time:", datetime.now())
                for i in range(self.num_cores):
                    print("core{}: {}lines read".format(i, self.cores[i].count_read + self.cores[i].count_write))
            # if self.debug:
            #     print("Count:",self.count)
            #     print("Bus:", self.bus)
            #     print("Bus_send_queue", self.bus_send_queue)
            #     t = input()

    def print_stat(self, wfile=None):
        if wfile is None:
            print("--- General Stats ---")
            print("Protocol: {}".format("MSI" if self.protocol == 0 else "MESI"))
            print("Capacity : {}".format(self.capacity))
            print("Way : {}".format(self.ways))
            print("Block size: {}".format(self.block_size))
            print("The number of cores: {}".format(self.num_cores))
            for i in range(self.num_cores):
                self.cores[i].print_stat(wfile)
        else:
            wfile.write("--- General Stats ---\n")
            wfile.write("Protocol: {}\n".format("MSI" if self.protocol == 0 else "MESI"))
            wfile.write("Capacity : {}\n".format(self.capacity))
            wfile.write("Way : {}\n".format(self.ways))
            wfile.write("Block size: {}\n".format(self.block_size))
            wfile.write("The number of cores: {}\n".format(self.num_cores))
            for i in range(self.num_cores):
                self.cores[i].print_stat(wfile)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: $ python ic606_homework3.py #_of_cores protocol capacity associativity")
    else:
        args = [int(x) for x in sys.argv[1:]]
        homeworkbus = MulticoreBus(args[0], args[1], args[2], args[3], debug=True)
        homeworkbus.run_siumulation()
        homeworkbus.print_stat()
