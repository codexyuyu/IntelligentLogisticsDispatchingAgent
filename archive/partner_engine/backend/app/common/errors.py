"""SHARED: framework-free failure for explicitly unfinished modules."""
class FeatureNotImplemented(NotImplementedError):
    def __init__(self, feature: str, owner: str):
        self.feature = feature
        self.owner = owner
        super().__init__(f"{feature} is a scaffold; implementation owner: {owner}")
