from datetime import datetime
import sys
import os


class coreHW2():
    def __init__(self, input_width, input_ROB, input_reservation, trace_file_name, dump, to_file, debug_bool):
        self.issue_width = input_width  # N way superscalar
        self.reservation_size = input_reservation  # ROB_size / 2 or same as ROB_size
        self.ROB_size = input_ROB
        self.trace_file_name = trace_file_name
        self.trace_file = open(self.trace_file_name, "r")
        self.trace_count = 0
        self.trace_file_end = False

        self.ROB_entry = {"no": None, "operation": None, "value": None, "destination": None, "completed": None}
        self.ROB = []  # max len = self.ROB_size
        # ROB number starts at 1, but ROB list index starts at 0
        self.ROB_no = 1

        self.fetch_queue_entry = {"inst": None, "dest": None, "src1": None, "src2": None, "addr": None}
        self.fetch_queue = []  # max len = 2 * self.issue_width
        self.fetch_no = 1

        self.res_station_entry = {"ROB": None, "time_left": None, "busy": None, "execute": None,  "inst": None, "v1": None, "v2": None,
                                  "q1": None, "q2": None, "rs_no": None}
        self.res_station = []  # max len = self.ROB_size
        self.rs_table = [True] + [False] * self.reservation_size

        # Res_station number starts at 1, but list index starts at 0
        self.RAT_entry = {"ROB": None, "valid": True}  # valid True: has recent info, False: not recent info
        self.RAT = [self.RAT_entry.copy()] * 17  # max len: 17 (16 registers(R1-R16) in the RSA, starting with 1)
        # RAT No. 0 is dummy: it may have a garbage content.

        self.execution_unit = []  # stores the res station indexes of executing instruction

        self.ROB_pop_list = []
        self.rs_pop_list = []
        self.fetch_pop_list = []

        self.cnt_IntAlu = 0
        self.cnt_MemRead = 0
        self.cnt_MemWrite = 0

        self.to_file = to_file
        self.dump = dump
        self.debug = debug_bool
        self.show_all = True

    def new_ROB_no(self):
        # ROB is deleted always from top; this means you can get new ROB number with mod calculation.
        tmp = self.ROB_no
        self.ROB_no = (self.ROB_no + 1) if self.ROB_no < self.ROB_size else 1
        return tmp

    def new_fetch_no(self):
        tmp = self.fetch_no
        self.fetch_no = (self.fetch_no + 1) if self.fetch_no < self.issue_width else 1
        return tmp

    def new_rs_no(self):
        tmp = self.rs_table.index(False)
        self.rs_table[tmp] = True
        return tmp

    def free_rs(self, rs_no):
        self.rs_table[rs_no] = False

    def p_commit(self):
        commit_count = 0
        for rob_entry in self.ROB:
            # From the top, look up weather this ROB entry is completed.
            if rob_entry["completed"]:
                # If it is, it's going to be deleted from ROB.
                self.ROB_pop_list.append(rob_entry)
                if rob_entry["destination"]:
                    self.RAT[rob_entry["destination"]] = self.RAT_entry.copy()
                # Return related RAT into initial state.
                commit_count += 1
                if commit_count >= self.issue_width:
                    break
            else:
                # If not completed entry appears, stop deleting.
                break

    def p_execute(self):
        for i in range(len(self.res_station)):
            if self.res_station[i]["ROB"] in self.execution_unit:
                if self.res_station[i]["time_left"] == 0:
                    self.res_station[i]["busy"] = False
                    self.execution_unit.remove(self.res_station[i]["ROB"])
                else:
                    self.res_station[i]["time_left"] -= 1

        for instruction in self.res_station:
            # For each instructions in reservation station,
            if instruction["busy"] is False:
                # If that instruction is not busy,
                self.rs_pop_list.append(instruction)
                # This instruction is going to be deleted from reservation station. And also...
                for rob_entry in self.ROB:
                    if rob_entry["no"] == instruction["ROB"]:
                        # Find a entry on ROB related with this instruction.
                        rob_entry["completed"] = True
                        # Mark ROB's complete flag as true.
                        for res_entry in self.res_station:
                            # Let reservation station know that This rob entry has finished, so q1 and q2 can be v1 v2.
                            if res_entry["q1"] == rob_entry["no"]:
                                i = self.res_station.index(res_entry)
                                self.res_station[i]["v1"] = rob_entry["destination"]
                                self.res_station[i]["q1"] = None
                                self.res_station[i]["execute"] = True
                            if res_entry["q2"] == rob_entry["no"]:
                                i = self.res_station.index(res_entry)
                                self.res_station[i]["v2"] = rob_entry["destination"]
                                self.res_station[i]["q2"] = None
                                self.res_station[i]["execute"] = True
                        break

    def p_issue(self):
        issue_count = 0
        for instruction in self.res_station:
            if instruction["q1"] is None and instruction["q2"] is None and\
               instruction["execute"] and instruction["busy"] and instruction["time_left"] != 0:
                # Instruction executable immediately: send to execution unit.
                if instruction["ROB"]not in self.execution_unit:
                    self.execution_unit.append(instruction["ROB"])
                    issue_count += 1
            if issue_count >= self.issue_width:
                break

    def p_decode(self):
        for i in range(self.issue_width if len(self.fetch_queue) > self.issue_width else len(self.fetch_queue)):
            if not self.fetch_queue:
                # If fetch queue is empty, pass
                break
            elif len(self.ROB) >= self.ROB_size:
                # If ROB is full, pass
                break
            elif len(self.res_station) >= self.reservation_size:
                # If reservation station is full, pass
                break

            # If non of above, proceed decoding.
            instruction = self.fetch_queue[i]
            self.fetch_pop_list.append(instruction)
            # Get the oldest instruction from fetch queue and delete it from fetch queue.
            ROB_no = self.new_ROB_no()
            # Get new ROB number(starts at 1)

            v1, v2 = instruction["src1"], instruction["src2"]
            q1, q2 = None, None
            # First, set the v1 v2 as src1 and src2 from instruction.
            execute = True
            # execution bool initialization.

            if v1 != 0:  # 0 is dummy
                if self.RAT[v1]["ROB"] is not None:  # That Register is used by other instruction.
                    if self.RAT[v1]["ROB"] != ROB_no:  # That register is not current instruction.
                        for rob_entry in self.ROB:
                            if rob_entry["no"] == self.RAT[v1]["ROB"]:  # Find the ROB with same ROB no in RAT.
                                if not rob_entry["completed"]:  # If it's completed, it's okay to run instantly.
                                    q1 = self.RAT[v1]["ROB"]
                                    execute = False

            if v2 != 0:  # 0 is dummy
                if self.RAT[v2]["ROB"] is not None:  # That Register is used by other instruction.
                    if self.RAT[v2]["ROB"] != ROB_no:  # That register is not current instruction.
                        for rob_entry in self.ROB:
                            if rob_entry["no"] == self.RAT[v2]["ROB"]:  # Find the ROB with same ROB no in RAT.
                                if not rob_entry["completed"]:  # If it's completed, it's okay to run instantly.
                                    q2 = self.RAT[v2]["ROB"]
                                    execute = False
            if instruction["dest"] != 0:
                if self.RAT[instruction["dest"]]["ROB"] is not None:  # Destination register is used by other instruction.
                    for j in self.ROB:  # in ROB, find that instruction.
                        if j["no"] == self.RAT[instruction["dest"]]["ROB"]:
                            self.ROB[self.ROB.index(j)]["destination"] = 0
                            # Make its destination into dummy(0) so it won't affect current instruction.
                            break
            self.RAT[instruction["dest"]] = {"ROB": ROB_no, "valid": False}
            # destination register already in use is not a problem: just overwrite it.

            # Make a new entry on ROB
            self.ROB.append({"no": ROB_no,
                             "operation": instruction["inst"],
                             "value": None,
                             "destination": None if instruction["dest"] == 0 else instruction["dest"],
                             "completed": False})

            # Make a new entry on reservation station.
            self.res_station.append({"ROB": ROB_no,
                                     "time_left": (3 if instruction["inst"] == "MemRead" else 1),
                                     "busy": True,
                                     "execute": execute,
                                     "inst": instruction["inst"],
                                     "v1": v1,
                                     "v2": v2,
                                     "q1": q1,
                                     "q2": q2,
                                     "rs_no": self.new_rs_no()})

    def p_fetch(self):
        # eliminating inner None is done in decode state
        if self.trace_file_end:
            return False
        else:
            while True:
                one_line = self.trace_file.readline()
                if one_line:
                    if one_line.endswith("\n"):
                        one_line = one_line[:-1]
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
                                             "addr": tmp[4],
                                             "no": self.new_fetch_no()})
                    # (inst_type, dest, src1, src2, addr_hex)
                else:
                    self.trace_file_end = True
                    self.trace_file.close()
                    break
                if len(self.fetch_queue) >= 2 * self.issue_width:
                    break

            return True

    def update_popped(self):
        for i in self.ROB_pop_list:
            self.ROB.remove(i)
        for j in self.rs_pop_list:
            self.free_rs(j["rs_no"])
            self.res_station.remove(j)
        for k in self.fetch_pop_list:
            self.fetch_queue.remove(k)
        self.ROB_pop_list, self.rs_pop_list, self.fetch_pop_list = [], [], []

    def run_simulation(self):
        count = 0
        start_time = datetime.now()
        if self.debug:
            print("Starting time: ", str(start_time))
        while True:
            count += 1
            self.p_commit()
            self.p_issue()
            self.p_execute()
            self.p_decode()
            self.p_fetch()
            self.update_popped()

            if self.debug:
                if self.show_all:
                    print("execution_unit", self.execution_unit)
                    for i in self.RAT:
                        print(i)
                    for i in self.res_station:
                        print(i)
                    for i in self.ROB:
                        print(i)
                    c = input("")
                    if c != "":
                        self.show_all = False
                if count % 500000 == 0:
                    current_time = datetime.now()
                    print(str(current_time), ",", count, "th cycle,", str(current_time - start_time), "passed")

            if self.dump == 1 or self.dump == 2:
                print("= Cycle: ", count)
                if self.dump == 2:
                    reservation_station_table = ["NOT BUSY"] * (self.reservation_size + 1)
                    for i in self.res_station:
                        src1 = i["v1"] if i["q1"] is None else "ROB" + str(i["q1"])
                        src2 = i["v2"] if i["q2"] is None else "ROB" + str(i["q2"])
                        reservation_station_table[i["rs_no"]] = "ROB" + str(i["ROB"]) + " " + str(src1) + " " + str(src2)
                    for i in range(1, self.reservation_size + 1):
                        print("RS" + str(i) + " : " + reservation_station_table[i])
                for i in self.ROB:
                    print("ROB" + str(i["no"]), " : ", ("C" if i["completed"] else "P"))
                print("")

            if self.trace_file_end and not self.ROB and not self.res_station:
                break
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
        if self.to_file:
            if not os.path.exists("./results/"):
                os.mkdir("./results/")
            with open("./results/{}_{}_{}_{}.txt".format(str(self.issue_width), str(self.ROB_size),
                      str(self.reservation_size), self.trace_file_name.split("/")[2].split("_")[2].split(".")[0]),
                      "w") as wfile:
                wfile.write(str(self.issue_width) + "\n")
                wfile.write(str(self.ROB_size) + "\n")
                wfile.write(str(self.reservation_size) + "\n")
                wfile.write(str(self.trace_file_name) + "\n")
                wfile.write("Cycles " + str(count) + "\n")
                wfile.write("IPC " + str(self.trace_count / count) + "\n")
                wfile.write("Total Insts " + str(self.trace_count) + "\n")
                wfile.write("IntAlu " + str(self.cnt_IntAlu) + "\n")
                wfile.write("MemRead " + str(self.cnt_MemRead) + "\n")
                wfile.write("MemWrite " + str(self.cnt_MemWrite) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: $ python ic606_homework2.py config.txt (trace_file).out")
    else:
        with open(sys.argv[1], "r") as config:
            dump = int(config.readline())
            width = int(config.readline())
            ROB_size = int(config.readline())
            Reservation_size = int(config.readline())

        OOO_core = coreHW2(width, ROB_size, Reservation_size, "./HW2_workloads/" + sys.argv[2], dump, False, True)
        # issue width: 1~8, RS size: rob/2 or rob, rob size: 16-512
        OOO_core.run_simulation()