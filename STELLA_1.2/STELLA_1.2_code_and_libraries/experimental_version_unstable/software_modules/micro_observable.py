class Observable:
    """An observer can get called when some object updates a value.
        class TheObserver:
            subscribable = 'someproperty'
            def something(self):
                theObserved.subscribe( observer.tellme )
            def tellme(self, property_name, value):
                it changed!
        The observed has to explicitly publish
        class TheObserved(Observable):
            def __init__(self):
                super.__init__()
            def someinterestingaction(self):
                self.someproperty = new value
                do other interresting things
                # Now the observer sees it!
                self.publish( 'someproperty' )
    """

    def __init__(self):
        self._subs = {}

    def subscribe(self, callback):
        """For the single ._subscribable property"""
        self._subscribe( self._subscribable, callback)

    def _subscribe(self, prop, callback):
        """Sign up for a specific property name."""
        if prop not in self._subs:
            self._subs[prop] = []
        self._subs[prop].append(callback)

    def publish(self, prop, value):
        """Explicitly notify subscribers of a change: subscriber.callback(property_name, value)
        """
        for cb in self._subs.get(prop, []):
            cb(prop, value)

