# global
from typing import Union, List, Optional, Sequence

import numpy as np
import torch
from torch import Tensor

# local
import ivy

# from ivy.functional.backends.numpy.data_type import as_ivy_dtype
from ivy.functional.ivy.creation import (
    asarray_to_native_arrays_and_back,
    asarray_infer_device,
    asarray_handle_nestable,
    NestedSequence,
    SupportsBufferProtocol,
)


# Array API Standard #
# -------------------#


def _differentiable_linspace(start, stop, num, *, device, dtype=None):
    if num == 1:
        return torch.unsqueeze(start, 0)
    n_m_1 = num - 1
    increment = (stop - start) / n_m_1
    increment_tiled = increment.repeat(n_m_1)
    increments = increment_tiled * torch.linspace(
        1, n_m_1, n_m_1, device=device, dtype=dtype
    )
    res = torch.cat(
        (torch.unsqueeze(torch.tensor(start, dtype=dtype), 0), start + increments), 0
    )
    return res


# noinspection PyUnboundLocalVariable,PyShadowingNames
def arange(
    start: float,
    /,
    stop: Optional[float] = None,
    step: float = 1,
    *,
    dtype: Optional[Union[ivy.Dtype, torch.dtype]] = None,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    if stop is None:
        stop = start
        start = 0
    if (step > 0 and start > stop) or (step < 0 and start < stop):
        if isinstance(stop, float):
            stop = float(start)
        else:
            stop = start
    if dtype is None:
        if isinstance(start, int) and isinstance(stop, int) and isinstance(step, int):
            return torch.arange(
                start, stop, step=step, dtype=torch.int64, device=device, out=out
            ).to(torch.int32)
        else:
            return torch.arange(start, stop, step=step, device=device, out=out)
    else:
        dtype = ivy.as_native_dtype(ivy.default_dtype(dtype=dtype))
        return torch.arange(start, stop, step=step, dtype=dtype, device=device, out=out)


arange.support_native_out = True
arange.unsupported_dtypes = ("float16",)


@asarray_to_native_arrays_and_back
@asarray_infer_device
@asarray_handle_nestable
def asarray(
    obj: Union[
        torch.Tensor,
        np.ndarray,
        bool,
        int,
        float,
        NestedSequence,
        SupportsBufferProtocol,
    ],
    /,
    *,
    copy: Optional[bool] = None,
    dtype: Optional[Union[ivy.Dtype, torch.dtype]] = None,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    if isinstance(obj, torch.Tensor) and dtype is None:
        dtype = obj.dtype
    elif isinstance(obj, (list, tuple, dict)) and len(obj) != 0:
        if dtype is None:
            dtype = ivy.default_dtype(item=obj, as_native=True)

        # if `obj` is a list of specifically tensors
        if isinstance(obj[0], torch.Tensor):
            if copy is True:
                return (
                    torch.stack([torch.as_tensor(i, dtype=dtype) for i in obj])
                    .clone()
                    .detach()
                    .to(device)
                )
            else:
                return torch.stack(
                    tuple([torch.as_tensor(i, dtype=dtype) for i in obj])
                ).to(device)

        # if obj is a list of other objects, expected to be a numerical type.
        else:
            if copy is True:
                return torch.as_tensor(obj, dtype=dtype).clone().detach().to(device)
            else:
                return torch.as_tensor(obj, dtype=dtype).to(device)

    elif isinstance(obj, np.ndarray) and dtype is None:
        dtype = ivy.as_native_dtype(ivy.as_ivy_dtype(obj.dtype.name))
    else:
        dtype = ivy.as_native_dtype((ivy.default_dtype(dtype=dtype, item=obj)))

    if dtype == torch.bfloat16 and isinstance(obj, np.ndarray):
        if copy is True:
            return (
                torch.as_tensor(obj.tolist(), dtype=dtype).clone().detach().to(device)
            )
        else:
            return torch.as_tensor(obj.tolist(), dtype=dtype).to(device)

    if copy is True:
        return torch.as_tensor(obj, dtype=dtype).clone().detach().to(device)
    else:
        return torch.as_tensor(obj, dtype=dtype).to(device)


def empty(
    shape: Union[ivy.NativeShape, Sequence[int]],
    *,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    return torch.empty(
        shape,
        dtype=dtype,
        device=device,
        out=out,
    )


empty.support_native_out = True


def empty_like(
    x: torch.Tensor,
    /,
    *,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    return torch.empty_like(x, dtype=dtype, device=device)


def eye(
    n_rows: int,
    n_cols: Optional[int] = None,
    /,
    *,
    k: int = 0,
    batch_shape: Optional[Union[int, Sequence[int]]] = None,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    if n_cols is None:
        n_cols = n_rows
    if batch_shape is None:
        batch_shape = []
    i = torch.eye(n_rows, n_cols, dtype=dtype, device=device)
    reshape_dims = [1] * len(batch_shape) + [n_rows, n_cols]
    tile_dims = list(batch_shape) + [1, 1]
    return_mat = torch.reshape(i, reshape_dims).repeat(tile_dims)

    # k=index of the diagonal. A positive value refers to an upper diagonal,
    # a negative value to a lower diagonal, and 0 to the main diagonal.
    # Default: 0.
    # value of k ranges from -n_rows < k < n_cols

    if k == 0:  # refers to the main diagonal
        ret = return_mat

    # when k is negative
    elif -n_rows < k < 0:
        mat = torch.concat(
            [
                torch.zeros([-k, n_cols], dtype=dtype, device=device, out=out),
                i[: n_rows + k],
            ],
            0,
        )
        ret = torch.reshape(mat, reshape_dims).repeat(tile_dims)

    # when k is positive
    elif 0 < k < n_cols:
        mat = torch.concat(
            [
                torch.zeros([n_rows, k], dtype=dtype, device=device, out=out),
                i[:, : n_cols - k],
            ],
            1,
        )
        ret = torch.reshape(mat, reshape_dims).repeat(tile_dims)
    else:
        ret = torch.zeros(
            batch_shape + [n_rows, n_cols], dtype=dtype, device=device, out=out
        )
    if out is not None:
        return ivy.inplace_update(out, ret)
    return ret


eye.support_native_out = True
eye.unsupported_dtypes = ("bfloat16",)


def from_dlpack(x, /, *, out: Optional[torch.Tensor] = None):
    x = x.detach() if x.requires_grad else x
    return torch.utils.dlpack.from_dlpack(x)


def full(
    shape: Union[ivy.NativeShape, Sequence[int]],
    fill_value: Union[int, float, bool],
    *,
    dtype: Optional[Union[ivy.Dtype, torch.dtype]] = None,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> Tensor:
    dtype = ivy.default_dtype(dtype=dtype, item=fill_value, as_native=True)
    ivy.assertions.check_fill_value_and_dtype_are_compatible(fill_value, dtype)
    if isinstance(shape, int):
        shape = (shape,)
    return torch.full(
        shape,
        fill_value,
        dtype=dtype,
        device=device,
        out=out,
    )


full.support_native_out = True


def full_like(
    x: torch.Tensor,
    /,
    fill_value: Union[int, float],
    *,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    ivy.assertions.check_fill_value_and_dtype_are_compatible(fill_value, dtype)
    return torch.full_like(x, fill_value, dtype=dtype, device=device)


def linspace(
    start: Union[torch.Tensor, float],
    stop: Union[torch.Tensor, float],
    /,
    num: int,
    *,
    axis: Optional[int] = None,
    endpoint: bool = True,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    if not endpoint:
        ans = linspace_helper(start, stop, num + 1, axis, device=device, dtype=dtype)
        ans = ans[:-1]
    else:
        ans = linspace_helper(start, stop, num, axis, device=device, dtype=dtype)
    if (
        endpoint
        and ans.shape[0] > 1
        and (not isinstance(start, torch.Tensor))
        and (not isinstance(stop, torch.Tensor))
    ):
        ans[-1] = stop
    if (
        ans.shape[0] >= 1
        and (not isinstance(start, torch.Tensor))
        and (not isinstance(stop, torch.Tensor))
        and ans[0] != start
    ):
        ans[0] = start
    return ans


linspace.support_native_out = True
linspace.unsupported_device_and_dtype = {"cpu": ("float16",)}


def linspace_helper(start, stop, num, axis=None, *, device, dtype):
    num = num.detach().numpy().item() if isinstance(num, torch.Tensor) else num
    start_is_array = isinstance(start, torch.Tensor)
    stop_is_array = isinstance(stop, torch.Tensor)
    linspace_method = torch.linspace
    sos_shape = []
    if start_is_array:
        start_shape = list(start.shape)
        sos_shape = start_shape
        if num == 1:
            if axis is not None:
                return start.unsqueeze(axis).to(device)
            else:
                return start.unsqueeze(-1).to(device)
        start = start.reshape((-1,))
        linspace_method = (
            _differentiable_linspace if start.requires_grad else torch.linspace
        )
    if stop_is_array:
        stop_shape = list(stop.shape)
        sos_shape = stop_shape
        if num == 1:
            return (
                torch.ones(
                    stop_shape[:axis] + [1] + stop_shape[axis:],
                    device=device,
                )
                * start
            )
        stop = stop.reshape((-1,))
        linspace_method = (
            _differentiable_linspace if stop.requires_grad else torch.linspace
        )
    if start_is_array and stop_is_array:
        if num < start.shape[0]:
            start = start.unsqueeze(-1)
            stop = stop.unsqueeze(-1)
            diff = stop - start
            inc = diff / (num - 1)
            res = [start]
            res += [start + inc * i for i in range(1, num - 1)]
            res.append(stop)
        else:
            res = [
                linspace_method(strt, stp, num, device=device, dtype=dtype)
                for strt, stp in zip(start, stop)
            ]
        torch.cat(res, -1).reshape(start_shape + [num])
    elif start_is_array and not stop_is_array:
        if num < start.shape[0]:
            start = start.unsqueeze(-1)
            diff = stop - start
            inc = diff / (num - 1)
            res = [start]
            res += [start + inc * i for i in range(1, num - 1)]
            res.append(torch.ones_like(start, device=device, dtype=dtype) * stop)
        else:
            res = [
                linspace_method(strt, stop, num, device=device, dtype=dtype)
                for strt in start
            ]
    elif not start_is_array and stop_is_array:
        if num < stop.shape[0]:
            stop = stop.unsqueeze(-1)
            diff = stop - start
            inc = diff / (num - 1)
            res = [torch.ones_like(stop, device=device, dtype=dtype) * start]
            res += [start + inc * i for i in range(1, num - 1)]
            res.append(stop)
        else:
            res = [
                linspace_method(start, stp, num, device=device, dtype=dtype)
                for stp in stop
            ]
    else:
        return linspace_method(start, stop, num, device=device, dtype=dtype)
    res = torch.cat(res, -1).reshape(sos_shape + [num])
    if axis is not None:
        res = torch.transpose(res, axis, -1)
    return res.to(device)


def meshgrid(
    *arrays: torch.Tensor, sparse: bool = False, indexing="xy"
) -> List[torch.Tensor]:
    if not sparse:
        return list(torch.meshgrid(*arrays, indexing=indexing))

    sd = (1,) * len(arrays)
    res = [
        torch.reshape(torch.as_tensor(a), (sd[:i] + (-1,) + sd[i + 1 :]))
        for i, a in enumerate(arrays)
    ]

    if indexing == "xy" and len(arrays) > 1:
        res[0] = torch.reshape(res[0], (1, -1) + sd[2:])
        res[1] = torch.reshape(res[1], (-1, 1) + sd[2:])

    return res


def ones(
    shape: Union[ivy.NativeShape, Sequence[int]],
    *,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    return torch.ones(shape, dtype=dtype, device=device)


ones.support_native_out = True


def ones_like_v_0p4p0_and_above(
    x: torch.Tensor,
    /,
    *,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    return torch.ones_like(x, dtype=dtype, device=device)


def ones_like_v_0p3p0_to_0p3p1(
    x: torch.Tensor,
    /,
    *,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    return torch.ones_like(x, out=out)


def tril(
    x: torch.Tensor, /, *, k: int = 0, out: Optional[torch.Tensor] = None
) -> torch.Tensor:
    return torch.tril(x, diagonal=k, out=out)


tril.support_native_out = True


def triu(
    x: torch.Tensor, /, *, k: int = 0, out: Optional[torch.Tensor] = None
) -> torch.Tensor:
    return torch.triu(x, diagonal=k, out=out)


triu.support_native_out = True


def zeros(
    shape: Union[ivy.NativeShape, Sequence[int]],
    *,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> Tensor:
    return torch.zeros(shape, dtype=dtype, device=device, out=out)


zeros.support_native_out = True


def zeros_like(
    x: torch.Tensor,
    /,
    *,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    return torch.zeros_like(x, dtype=dtype, device=device)


# Extra #
# ------#


array = asarray


def copy_array(x: torch.Tensor, *, out: Optional[torch.Tensor] = None) -> torch.Tensor:
    return x.clone()


def logspace(
    start: Union[torch.Tensor, int],
    stop: Union[torch.Tensor, int],
    /,
    num: int,
    *,
    base: float = 10.0,
    axis: Optional[int] = None,
    dtype: torch.dtype,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    power_seq = ivy.linspace(start, stop, num, axis=axis, dtype=dtype, device=device)
    return base**power_seq


logspace.support_native_out = True
logspace.unsupported_device_and_dtype = {"cpu": ("float16",)}


def one_hot(
    indices: torch.Tensor,
    depth: int,
    /,
    *,
    on_value: Optional[torch.Tensor] = None,
    off_value: Optional[torch.Tensor] = None,
    axis: Optional[int] = None,
    dtype: Optional[torch.dtype] = None,
    device: torch.device,
    out: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    on_none = on_value is None
    off_none = off_value is None

    if dtype is None:
        if on_none and off_none:
            dtype = torch.float32
        else:
            if not on_none:
                dtype = torch.tensor(on_value).dtype
            elif not off_none:
                dtype = torch.tensor(off_value).dtype
    else:
        dtype = ivy.as_native_dtype(dtype)

    on_value = torch.tensor(1.0) if on_none else torch.tensor(on_value, dtype=dtype)
    off_value = torch.tensor(0.0) if off_none else torch.tensor(off_value, dtype=dtype)

    res = torch.nn.functional.one_hot(indices.to(torch.int64), depth)

    if not on_none or not off_none:
        res = torch.where(res == 1, on_value, off_value)

    if axis is not None:
        res = torch.moveaxis(res, -1, axis)

    return res.to(device, dtype)