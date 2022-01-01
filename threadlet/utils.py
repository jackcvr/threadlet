import typing
from concurrent.futures import _base


class FuturedFunc(typing.NamedTuple):
    future: _base.Future
    func: typing.Callable
    args: typing.Any = None
    kwargs: typing.Any = None

    def __call__(self, *args, **kwargs):
        if not self.future.set_running_or_notify_cancel():
            return

        try:
            args = args or self.args or ()
            kwargs = kwargs or self.kwargs or {}
            res = self.func(*args, **kwargs)
        except BaseException as e:
            self.future.set_exception(e)
            self = None
        else:
            self.future.set_result(res)
