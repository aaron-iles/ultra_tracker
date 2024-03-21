#!/usr/bin/env python3

import queue
import threading

import requests


# Worker function to process POST requests from the queue
def issue_posts(q):
    while True:
        kwargs = q.get()
        response = requests.post(**kwargs)
        q.task_done()


post_queue = queue.Queue()

# Start a worker thread to process POST requests
for _ in range(10):
    worker_thread = threading.Thread(target=issue_posts, args=(post_queue,))
    worker_thread.daemon = True  # Daemonize the thread so it exits when the main program exits
    worker_thread.start()
