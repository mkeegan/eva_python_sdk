import threading
import re

from jsonmerge import merge

class threadsafe_JSON:
    """
    threadsafe_JSON is an JOSN object wrapped in a mutex for threadsafe getting and setting.
    Set is a reserved keyword in python so we'll use update instead. Use merge update the
    structure with changes from the suppied object.
    """
    def __init__(self):
        self.object_lock = threading.Lock()
        self.object = None


    def update(self, obj):
            self.object_lock.acquire()
            self.object = obj
            self.object_lock.release()


    def get(self):
            self.object_lock.acquire()
            obj = self.object
            self.object_lock.release()
            return obj 


    def merge_update(self, changes):
            self.object_lock.acquire()
            obj = self.object

            # TODO may need to check that merge was successful
            # TODO can this throw?
            merged_obj = merge(obj, changes)

            self.object = merged_obj
            self.object_lock.release()
            return obj


def strip_ip(host_address):
    """
    strip_ip will remove http and ws prefixes from a host address
    """
    regex = re.compile(r"(https)?(http)?(ws)?://(www\.)?")
    new = regex.sub('', host_address).strip().strip('/')

    return new
