#!/usr/bin/env python3

import queue
import threading

import requests


post_queue = queue.Queue()


# Worker function to process POST requests from the queue
def issue_posts(pq: queue.Queue) -> None:
    """
    This worker function processes POSTs from the queue.

    :param queue.Queue pq: A Queue object from which to pull tasks.
    :return None:
    """
    while True:
        kwargs = pq.get()
        response = requests.post(**kwargs)
        pq.task_done()


def start_post_workers(num: int) -> None:
    """
    This function starts the workers for the POST queue.

    :param int num: The number of threaded workers to start.
    :return None:
    """
    for _ in range(num):
        worker_thread = threading.Thread(target=issue_posts, args=(post_queue,))
        worker_thread.daemon = True  # Daemonize the thread so it exits when the main program exits
        worker_thread.start()

for _ in range(10):
    worker_thread = threading.Thread(target=issue_posts, args=(post_queue,))
    worker_thread.daemon = True  # Daemonize the thread so it exits when the main program exits
    worker_thread.start()

#start_post_workers(10)
