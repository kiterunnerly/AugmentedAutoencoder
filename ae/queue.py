# -*- coding: utf-8 -*-

import threading

import tensorflow as tf

from utils import lazy_property

class Queue(object):

    def __init__(self, dataset, num_threads, queue_size, batch_size):
        self._dataset = dataset
        self._num_threads = num_threads
        self._queue_size = queue_size
        self._batch_size = batch_size

        datatypes = 2*['float32']
        shapes = 2*[self._dataset.shape]

        batch_shape = [None]+list(self._dataset.shape)
        
        self._placeholders = 2*[
            tf.placeholder(dtype=tf.float32, shape=batch_shape),
            tf.placeholder(dtype=tf.float32, shape=batch_shape) 
        ]

        self._queue = tf.FIFOQueue(self._queue_size, datatypes, shapes=shapes)
        self.x, self.y = self._queue.dequeue_up_to(self._batch_size)
        self.enqueue_op = self._queue.enqueue_many(self._placeholders)

        self._coordinator = tf.train.Coordinator()

        self._threads = []


    def start(self, session):
        assert len(self._threads) == 0
        tf.train.start_queue_runners(session, self._coordinator)
        for _ in xrange(self._num_threads):
            thread = threading.Thread(
                        target=Queue.__run__, 
                        args=(self, session)
                        )
            thread.deamon = True
            thread.start()
            self._threads.append(thread)


    def stop(self, session):
        self._coordinator.request_stop()
        session.run(self._queue.close(cancel_pending_enqueues=True))
        self._coordinator.join(self._threads)
        self._threads[:] = []


    def __run__(self, session):
        while not self._coordinator.should_stop():
            batch = self._dataset.batch(self._batch_size)
            feed_dict = { k:v for k,v in zip( self._placeholders, batch ) }
            try:
                session.run(self.enqueue_op, feed_dict)
            except tf.errors.CancelledError as e:
                pass