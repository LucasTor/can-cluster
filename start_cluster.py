from concurrent.futures import ThreadPoolExecutor

from can_helper import read_can
from gpio_helper import read_io
from cluster import run_cluster
from model import SensorState

if __name__ == '__main__':
    state = SensorState()

    ex = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ftcan")
    can_reader   = ex.submit(read_can, state=state)
    io_reader   = ex.submit(read_io, state=state)

    run_cluster(state)
