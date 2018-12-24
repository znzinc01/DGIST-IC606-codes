import ic606_homework3 as hw3
import os

for i in [2, 4, 8]:
    for j in [0, 1]:
        for k in [64,128, 256]:
            for l in [4, 8]:
                print("num_cores: {}, protocol: {}, capacity: {}, associativity: {}".format(i, j, k, l))
                mcore = hw3.MulticoreBus(i, j, k, l, False)
                mcore.run_siumulation()
                if not os.path.exists("./results/"):
                    os.mkdir("./results/")
                with open("./results/{}_{}_{}_{}.txt".format(i, j, k, l), "w") as wfile:
                    mcore.print_stat(wfile)
