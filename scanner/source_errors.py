"""Explicit integration states, distinct from temporary network failures."""


class IntegrationPending(RuntimeError):
    pass
