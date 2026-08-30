
import logging

import cocotb
import socket
import struct 
import errno
import zmq
from cocotb.queue import Queue
from cocotb.triggers import Event, First, Timer, NullTrigger
from cocotb.utils import get_sim_time, get_sim_steps
from .tlp import Tlp
from .tlp import TlpFmt


class CosimPort:
    """Cosim socket port"""
    def __init__(self, port: int = 5555, push_port: int = 6001, pull_port: int = 6000, *args, **kwargs):
        self.parent = None
        self.rx_handler = None

        self.tx_queue = Queue(1)
        self.tx_queue_sync = Event()

        self.rx_queue = Queue()
        self.port = port
        self.push_port = push_port
        self.pull_port = pull_port
        self.cosim_sock = None

        cocotb.start_soon(self._run_receive())
        cocotb.start_soon(self._run_transmit())


    def start_cosim_server(self, hostname):
        context = zmq.Context()
        self.cosim_sock = context.socket(zmq.REP)

        print(f"PCIe cosim listening on {self.port}")
        self.cosim_sock.bind(f"tcp://localhost:{self.port}")

        # pull socket for incoming posted transcations
        self.pull_socket = context.socket(zmq.PULL)
        print(f"PCIe cosim listening on {self.pull_port}")
        self.pull_socket.bind(f"tcp://localhost:{self.pull_port}")

        # push socket for outgoing posted transactions
        self.push_socket = context.socket(zmq.PUSH)
        print(f"PCIe cosim listening on {self.push_port}")
        self.push_socket.bind(f"tcp://localhost:{self.push_port}")
        cocotb.start_soon(self._socket_recv())

        poller = zmq.Poller()
        poller.register(self.cosim_sock, zmq.POLLIN)
        poller.register(self.pull_socket, zmq.POLLIN)
        self.poller = poller


    async def send(self, pkt):
        await self.tx_queue.put(pkt)
        self.tx_queue_sync.set()

    async def _run_receive(self):
        while True:
            tlp = await self.rx_queue.get()
            if self.rx_handler is None:
                raise Exception("Receive handler not set")
            await self.rx_handler(tlp)

    async def _run_transmit(self):
        await NullTrigger()
        while True:
            while self.tx_queue.empty():
                self.tx_queue_sync.clear()
                await self.tx_queue_sync.wait()
            pkt = self.tx_queue.get_nowait()
            self.log.debug("Send TLP %s", pkt)
            await self._socket_send(pkt)

    async def _socket_send(self, pkt):
        if pkt.is_read_write():
            self.log.debug("Sending on push socket")
            socket = self.push_socket
        else:
            self.log.debug("Sending on rep socket")
            socket = self.cosim_sock

        tlp_bytes = pkt.pack()
        tlp_len = len(pkt.data)
        socket.send(tlp_bytes, tlp_len)

    async def _socket_recv(self):
        while True:
            sock_list = dict(self.poller.poll(0))
            if self.cosim_sock in sock_list and sock_list[self.cosim_sock] == zmq.POLLIN:
                message = self.cosim_sock.recv()
                tlp = Tlp.unpack(message)
                self.rx_queue.put_nowait(tlp)
            if self.pull_socket in sock_list and sock_list[self.pull_socket] == zmq.POLLIN:
                message = self.pull_socket.recv()
                tlp = Tlp.unpack(message)
                self.rx_queue.put_nowait(tlp)
            await Timer(10, "ns")

