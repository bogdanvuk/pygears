class SimEvent(list):
    """Simulator Event that can trigger list of callbacks.

    Event is implemented as a list of callable objects - callbacks.
    Calling an instance of this will cause a call to each item in
    the list in ascending order by index.

    Callback function should return a boolean value. If it returns:

    True    -- Callback is re-registered by the _event
    False   -- Callback is deleted from the list

    Callback can be registered with or without arguments. Callback
    without arguments is registered by adding function reference
    to the list. Callback with arguments is registered by adding
    a tuple to the list. The first tuple item contains function
    reference. The rest of the items will be passed to the
    callback once the _event is triggered.
    """

    def __call__(self, *args, **kwargs):
        """Trigger the _event and call the callbacks.

        The arguments passed to this function will be passed to
        all the callbacks.
        """

        expired = []

        for i, f in enumerate(self):
            # If additional callback arguments are passed
            if isinstance(f, tuple):
                func = f[0]
                fargs = f[1:]

                ret = func(*(fargs + args), **kwargs)
            else:
                ret = f(*args, **kwargs)

            # If callback should not be re-registered
            if not ret:
                expired.append(i)

        # Delete from the list all callback that returned false
        for e in reversed(expired):
            del self[e]

    def __repr__(self):
        return "Event(%s)" % list.__repr__(self)
