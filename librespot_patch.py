"""
make librespot-python safe for several sessions in one process.

librespot-python 0.0.x keeps its request bookkeeping (callbacks, sequence
numbers, the queue an audio key answer is delivered through, ...) in *class*
attributes, so every Session shares them. With more than one logged-in account
the accounts then steal each other's answers: audio keys land in the wrong
download ("Empty()" / "Failed fetching audio key") and, worse, can decrypt
with another request's key.

apply() gives every instance its own copy of that state. It only touches the
names that exist, so it keeps working if the library changes.
"""

import queue
import threading

_APPLIED = False


def _per_instance(cls, **factories):
    """give every new instance of cls its own copy of the (name-mangled) attributes"""

    wanted = {
        name: factory
        for name, factory in factories.items()
        if hasattr(cls, f"_{cls.__name__}__{name}")
    }
    original_init = cls.__init__

    def __init__(self, *args, **kwargs):
        for name, factory in wanted.items():
            setattr(self, f"_{cls.__name__}__{name}", factory())

        original_init(self, *args, **kwargs)

    cls.__init__ = __init__


def apply():
    """patch librespot once"""

    global _APPLIED  # pylint: disable=global-statement

    if _APPLIED:
        return

    from librespot.audio import AudioKeyManager
    from librespot.mercury import MercuryClient

    _per_instance(AudioKeyManager, callbacks=dict, seq_holder=int)
    _per_instance(
        AudioKeyManager.SyncCallback, reference=queue.Queue, reference_lock=threading.Condition
    )
    _per_instance(
        MercuryClient, callbacks=dict, partials=dict, seq_holder=int, subscriptions=list
    )
    _per_instance(MercuryClient.SyncCallback, reference=queue.Queue)

    _APPLIED = True
