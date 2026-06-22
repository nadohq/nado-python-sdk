from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import Any, Callable, Type, TypeVar, Union


class NadoBaseModel(BaseModel):
    """
    This base model extends Pydantic's BaseModel and excludes fields with None
    values by default when serializing via .dict() or .json().

    `.dict()` / `.json()` are retained as the SDK's serialization surface (the
    server protocol omits null fields); they delegate to Pydantic v2's
    `model_dump` / `model_dump_json` rather than the deprecated v1 methods.

    `serialize_as_any=True` is forced so values are serialized by their runtime
    type rather than the declared field type. The request models intentionally
    swap a field's value for a differently-shaped model in a validator (e.g. a
    `*Params` field becomes a `TxRequest`); v1 serialized the runtime value
    duck-typed, and this preserves that behavior under v2.

    `coerce_numbers_to_str` keeps v1's tolerance for the server returning
    numbers where the models declare strings (e.g. `chain_id`, nonces, x18
    amounts).

    `revalidate_instances="always"` restores v1 `parse_obj` semantics: passing a
    model instance through `model_validate` yields a fresh, independent copy.
    The clients rely on this — e.g. `place_order` normalizes its input with
    `model_validate` and mutates the result, and callers must be able to reuse
    the original params object across calls without state leaking between them.
    """

    model_config = ConfigDict(
        coerce_numbers_to_str=True, revalidate_instances="always"
    )

    def dict(self, **kwargs):
        """
        Convert model to dictionary, excluding None fields by default.

        Args:
            kwargs: Arbitrary keyword arguments.

        Returns:
            dict: The model as a dictionary.
        """
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("serialize_as_any", True)
        return self.model_dump(**kwargs)

    def json(self, **kwargs):
        """
        Convert model to JSON, excluding None fields by default.

        Args:
            kwargs: Arbitrary keyword arguments.

        Returns:
            str: The model as a JSON string.
        """
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("serialize_as_any", True)
        return self.model_dump_json(**kwargs)

    def serialize_dict(self, fields: list[str], func: Callable):
        """
        Apply a function to specified fields in the model's dictionary.

        Args:
            fields (list[str]): Fields to be modified.

            func (Callable): Function to apply to each field.
        """
        for field in fields:
            self.__dict__[field] = func(self.__dict__[field])


def parse_enum_value(value: Union[str, Enum]) -> str:
    """
    Utility function to parse an enum value.

    Args:
        value (str | Enum): Original value which may be an Enum.

    Returns:
        str: The Enum value.
    """
    if isinstance(value, Enum):
        return value.value
    else:
        return value


T = TypeVar("T")


def ensure_data_type(data, expected_type: Type[T]) -> T:
    assert isinstance(
        data, expected_type
    ), f"Expected {expected_type.__name__}, but got {type(data).__name__}"
    return data


def is_instance_of_union(obj: Any, union) -> bool:
    """Check if `obj` is an instance of any type in the `union`."""
    return any(isinstance(obj, cls) for cls in union.__args__)
