"""Bounded handling of transient Windows file-sharing locks."""
import os
import time

def atomic_replace(source,target):
    for delay in (.05,.1,.2,.4,.8,1.6,None):
        try:
            return source.replace(target)
        except PermissionError:
            if os.name!='nt' or delay is None:
                raise
            # A just-closed archive may still be inspected by another process.
            # Retry the same atomic operation; never relax permissions or AV.
            time.sleep(delay)
