from datetime import datetime

class coreHW2():
    def __init__(self, input_width, input_reservation, input_ROB, config_file_name, trace_file_name, debug_bool):
        self.issue_width = input_width  # N way superscalar
        self.reservation_size = input_reservation  # ROB_size / 2 or same as ROB_size
        self.ROB_size = input_ROB
        self.trace_file = open(trace_file_name, "r")
        self.trace_count = 0
        self.trace_file_end = False

        self.ROB_entry = {"no": None, "operation": None, "value": None, "destination": None, "completed": None}
        self.ROB = []  # max len = self.ROB_size
        self.ROB_no = 0
        self.fetch_queue_entry = {"inst": None, "dest": None, "src1": None, "src2": None, "addr": None}
        self.fetch_queue = []  # max len = 2 * self.issue_width
        self.res_station_entry = {"ROB": None, "time_left": None, "busy": None, "inst": None, "v1": None, "v2": None,
                                  "q1": None, "q2": None}
        self.res_station = []  # max len = self.ROB.size
        self.RAT_entry = {"ROB": None, "valid": True}  # valid True: has recent info, False: not recent info
        self.RAT = [self.RAT_entry.copy()] * 17  # max len: 17 (16 registers(R1-R16) in the RSA, starting with 1)

        self.execution_unit = []  # stores the res station indexes of executing instruction

        self.cnt_IntAlu = 0
        self.cnt_MemRead = 0
        self.cnt_MemWrite = 0

        self.debug = debug_bool

    def new_ROB_no(self):
        tmp = self.ROB_no
        self.ROB_no = (self.ROB_no + 1) if self.ROB_no < (self.ROB_size - 1) else 0
        return tmp

    def p_commit(self):
        pop_list = []
        for instruction in self.res_station:
            if instruction["time_left"] == 0:
                pop_list.append(instruction)
                for k in self.ROB:
                    if k["no"] == instruction["ROB"]:
                        k["completed"] = True
                        for l in self.res_station:
                            if l["q1"] == k["destination"]:
                                l["v1"] = l["q1"]
                                l["q1"] = None
                            elif l["q2"] == k["destination"]:
                                l["v2"] = l["q2"]
                                l["q2"] = None
                        break
        for j in pop_list:
            self.res_station.remove(j)

        pop_list = []
        for single_rob in self.ROB:
            if single_rob["completed"]:
                pop_list.append(single_rob)
                self.RAT[single_rob["destination"]] = self.RAT_entry.copy()
            else:
                break
        for j in pop_list:
            self.ROB.remove(j)

    def p_execute(self):
        for execution in self.execution_unit:
            self.res_station[execution]["time_left"] -= 1

    def p_issue(self):
        self.execution_unit = []
        issue_count = 0
        for i in range(len(self.res_station)):
            instruction = self.res_station[i]
            if instruction["q1"] is None and instruction["q2"] is None:
                self.execution_unit.append(int(i))
                issue_count += 1
            if issue_count == self.issue_width:
                break

    def p_decode(self):
        count = self.issue_width
        if not self.fetch_queue:
            # ff fetch queue is empty, pass
            pass
        elif len(self.ROB_entry) == self.ROB_size:
            # If ROB is full, pass
            pass
        elif len(self.res_station) == self.reservation_size:
            # If reservation station is full, pass
            pass
        else:
            while count > 0:
                instruction = self.fetch_queue.pop(0)
                ROB_no = self.new_ROB_no()

                self.RAT[instruction["dest"]] = {"ROB": ROB_no, "valid": False}
                # destination register already in use is not a problem: just overwrite it
                v1, v2 = instruction["src1"], instruction["src2"]
                if self.RAT[instruction["src1"]]["ROB"] is (not None and not 0 and not ROB_no):
                    v1, q1 = None, instruction["src1"]
                else:
                    v1, q1 = instruction["src1"], None
                if self.RAT[instruction["src2"]]["ROB"] is (not None and not 0 and not ROB_no):
                    v2, q2 = None, instruction["src2"]
                else:
                    v2, q2 = instruction["src2"], None

                self.ROB.append({"no": ROB_no,
                                 "operation": instruction["inst"],
                                 "value": None,
                                 "destination": instruction["dest"],
                                 "completed": False})
                self.res_station.append({"ROB": ROB_no,
                                         "time_left": (3 if instruction["inst"] == "MemRead" else 1),
                                         "busy": False,
                                         "inst": instruction["inst"],
                                         "v1": v1,
                                         "v2": v2,
                                         "q1": q1,
                                         "q2": q2})

                count -= 1

    def p_fetch(self):
        # eliminating inner None is done in decode state
        if self.trace_file_end:
            return False
        else:
            fetch_amount = (2 * self.issue_width) - len(self.fetch_queue)
            if fetch_amount > self.issue_width:
                fetch_amount = self.issue_width
            for i in range(fetch_amount):
                one_line = self.trace_file.readline()
                if one_line.endswith("\n"):
                    one_line = one_line[:-1]
                if one_line:
                    self.trace_count += 1
                    tmp = one_line.split()
                    if tmp[0] == "IntAlu":
                        self.cnt_IntAlu += 1
                    elif tmp[0] == "MemRead":
                        self.cnt_MemRead += 1
                    elif tmp[0] == "MemWrite":
                        self.cnt_MemWrite += 1
                    self.fetch_queue.append({"inst": tmp[0],
                                             "dest": int(tmp[1]),
                                             "src1": int(tmp[2]),
                                             "src2": int(tmp[3]),
                                             "addr": tmp[4]})
                    # (inst_type, dest, src1, src2, addr_hex)
                else:
                    self.trace_file_end = True
                    self.trace_file.close()
                    break
            return True


    def run_simulation(self):
        count = 0
        start_time = datetime.now()
        print("Starting time: ", str(start_time))
        print("Total lines: 1000,0000")
        while True:
            count += 1
            self.p_commit()
            self.p_issue()
            self.p_execute()
            self.p_decode()
            self.p_fetch()
            if self.trace_file_end and not self.ROB:
                break
            if count % 10000 == 0:
                current_time = datetime.now()
                print(str(current_time), ",", str(current_time - start_time), "passed,", count, "th cycle")
            if self.debug:
                print("Cycle: ", count)
                print("Fetch queue: ", self.fetch_queue)
                print("RAT: ", self.RAT)
                print("Execution Unit: ", self.execution_unit)
                print("ROB: ", self.ROB)
                print("Reservation station: ", self.res_station)
                t = input("")
        try:
            self.trace_file.close()
        except:
            pass

        print("Cycles", count)
        print("IPC", self.trace_count / count)
        print("Total Insts", self.trace_count)
        print("IntAlu", self.cnt_IntAlu)
        print("MemRead", self.cnt_MemRead)
        print("MemWrite", self.cnt_MemWrite)


OOO_core = coreHW2(4, 8, 16, None, "./HW2_workloads/hw2_trace_mcf.out", False)
# issue width: 1~8, RS size: rob/2 or rob, rob size: 16-512
OOO_core.run_simulation()