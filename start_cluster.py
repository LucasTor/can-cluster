from concurrent.futures import ThreadPoolExecutor

from can_helper import read_can
from cluster import run_cluster
import time

if __name__ == '__main__':
    data = {}
    def print_can(data):
        while True:
            print('RPM:', data.get('rpm', 0))
            time.sleep(0.1)
            # data['rpm'] = random.randint(1000, 8000)

    ex = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ftcan")
    can_reader   = ex.submit(read_can, data=data)

    run_cluster(data)
