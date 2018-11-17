class coreHW2():
    def __init__(self):
        pass

    def run_simulation(self):
        count = 0
        with open("./HW2_workloads/hw2_trace_mcf.out", "r") as trace_obj:
            for line in trace_obj:
                count += 1
                (inst_type, dest, src1, src2, addr_hex) = line.split()
                addr_dec = int("0x"+addr_hex, 0)
                print(inst_type, dest, src1, src2, addr_hex, addr_dec)
                if count == 10:
                    break


OOO_core = coreHW2()
OOO_core.run_simulation()