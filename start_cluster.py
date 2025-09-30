from concurrent.futures import ThreadPoolExecutor

from can_helper import read_can
from gpio_helper import read_io
from cluster import run_cluster
import time

if __name__ == '__main__':
    data = {}

    ex = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ftcan")
    can_reader   = ex.submit(read_can, data=data)
    io_reader   = ex.submit(read_io, data=data)

    run_cluster(data)
