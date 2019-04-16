import json
import asyncio
import time
import logging
import threading


from .helpers import (strip_ip, threadsafe_JSON)
from .robot_state import RobotState
from .eva_ws import ws_connect
from .eva_errors import (EvaConnectionError, EvaDisconnectionError)
from .eva_http_client import EvaHTTPClient


class EvaState:
    """
    TODO
    """
    def __init__(self, host_ip, token):
        http_client = EvaHTTPClient(host_ip, token)
        
        self.host_ip = host_ip
        self.token = token

        self.__logger = logging.getLogger('automata.Eva:{}'.format(host_ip))

        # Try connecting to Eva, this raises a EvaConnectionError is the host_ip is invalid
        try:
            snapshot = http_client.data_snapshot(mode='object')
        except Exception:
            raise EvaConnectionError("Unable to connect the Eva, please check Eva is online and connected to the network")

        # Create the threadsafe_JSON used to merge ws update events onto the Eva snapshot
        self.__state = threadsafe_JSON()
        self.__state.update(snapshot)

        self.__state_handler_function = None
        self.__async_running = True
        self.__ws_msg_count = 0

        # Start the async thread
        self.__thread = threading.Thread(target=self.__start_loop)
        self.__thread.start()

        # TODO need to check that websocket connects

    def __start_loop(self):
        self.__loop = asyncio.new_event_loop()
        self.__logger.debug("Async loop started")
        self.__loop.run_until_complete(self.__ws_update_handler())
        self.__logger.debug("Async loop stopped")

    # TODO need to handle exceptions and pass them to the main Eva object thread
    async def __ws_update_handler(self):
        self.__websocket = await ws_connect(self.host_ip, self.token)

        while self.__async_running:
            # ws_msg_json = await self.__websocket.recv()
            # TODO need to check messages are not dropped in the case that Timeout is hit
            try:
                ws_msg_json = await asyncio.wait_for(self.__websocket.recv(), timeout=1)
            except asyncio.TimeoutError:
                continue

            ws_msg = json.loads(ws_msg_json)

            # if '"type":"state_change"' not in ws_msg_json:
            #     print(ws_msg_json)

            if 'changes' in ws_msg:
                new_state = self.__state.merge_update(ws_msg['changes'])

                self.__logger.debug('ws msg received: {}'.format(self.__ws_msg_count))
                self.__ws_msg_count += 1

                if self.__state_handler_function is not None:
                    self.__state_handler_function(new_state)


        print('closing websocket')
        await self.__websocket.close()


    def close(self):
        """
        close() disconnects eva_object from Eva.
        close() is idempotent: it doesn’t do anything once the connection is closed.
        Once close() has been called you cannot reconnect with this object, make a
        new object instance instead.
        """
        if self.__async_running:
            self.__async_running = False
            self.__thread.join()


    def state(self):
        if not self.__async_running:
            raise EvaDisconnectionError()
        return self.__state.get()


    def add_state_change_handler(self, state_handler_function):
        if not self.__async_running:
            raise EvaDisconnectionError()

        if self.__state_handler_function is not None:
            raise ValueError

        # TODO lock needed
        self.__state_handler_function = state_handler_function


    def remove_state_change_handler(self):
        if not self.__async_running:
            raise EvaDisconnectionError()

        # TODO lock needed
        self.__state_handler_function = None
