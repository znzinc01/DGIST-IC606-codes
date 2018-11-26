import ic606_homework2 as hw2

file_list = ["hw2_trace_bzip2.out", "hw2_trace_mcf.out"]

for i in [1, 2, 4, 8]:
    for j in [16, 32, 64, 128, 256, 512]:
        for k in [j, j/2]:
            for l in file_list:
                print("Width:", i)
                print("ROB_size", j)
                print("reservation_size", k)
                print(l)
                ooo = hw2.coreHW2(8, 16, 8, "./HW2_workloads/" + l,
                                  0, True, False)
                ooo.run_simulation()
