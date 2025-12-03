from nado_protocol.utils.enum import StrEnum
from eth_account import Account
from eth_account.signers.local import LocalAccount
from typing import Optional, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    model_validator,
    AnyUrl,
    TypeAdapter,
)


class NadoBackendURL(StrEnum):
    """Enum representing different Nado backend URLs."""

    # dev
    DEVNET_GATEWAY = "http://localhost:80"
    DEVNET_INDEXER = "http://localhost:8000"
    DEVNET_TRIGGER = "http://localhost:8080"

    # testnets
    TESTNET_GATEWAY = "https://gateway.test.nado.xyz/v1"
    TESTNET_INDEXER = "https://archive.test.nado.xyz/v1"
    TESTNET_TRIGGER = "https://trigger.test.nado.xyz/v1"

    # mainnets
    MAINNET_GATEWAY = "https://gateway.prod.nado.xyz/v1"
    MAINNET_INDEXER = "https://archive.prod.nado.xyz/v1"
    MAINNET_TRIGGER = "https://trigger.prod.nado.xyz/v1"


PrivateKey = str
Signer = Union[LocalAccount, PrivateKey]


class NadoClientOpts(BaseModel):
    """
    Model defining the configuration options for execute Nado Clients (e.g: Engine, Trigger). It includes various parameters such as the URL,
    the signer, the linked signer, the chain ID, and others.

    Attributes:
        url (AnyUrl): The URL of the server.
        signer (Optional[Signer]): The signer for the client, if any. It can either be a `LocalAccount` or a private key.
        linked_signer (Optional[Signer]): An optional signer linked the main subaccount to perform executes on it's behalf.
        chain_id (Optional[int]): An optional network chain ID.
        endpoint_addr (Optional[str]): Nado's endpoint address used for verifying executes.

    Notes:
        - The class also includes several methods for validating and sanitizing the input values.
        - "linked_signer" cannot be set if "signer" is not set.
    """

    url: str
    signer: Optional[Union[LocalAccount, PrivateKey]] = None
    linked_signer: Optional[Signer] = None
    chain_id: Optional[int] = None
    endpoint_addr: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode='after')
    def check_linked_signer(self):
        """
        Validates that if a linked_signer is set, a signer must also be set.

        Returns:
            self
        """
        if self.linked_signer and not self.signer:
            raise ValueError("linked_signer cannot be set if signer is not set")
        return self

    @field_validator("url")
    @classmethod
    def clean_url(cls, v: Union[str, AnyUrl]) -> str:
        """
        Cleans the URL input by removing trailing slashes.

        Args:
            v (Union[str, AnyUrl]): The input URL.

        Returns:
            str: The cleaned URL.
        """
        TypeAdapter(AnyUrl).validate_python(v)
        return str(v).rstrip("/")

    @field_validator("signer")
    @classmethod
    def signer_to_local_account(cls, v: Optional[Signer]) -> Optional[LocalAccount]:
        """
        Validates and converts the signer to a LocalAccount instance.

        Args:
            v (Optional[Signer]): The signer instance or None.

        Returns:
            Optional[LocalAccount]: The LocalAccount instance or None.
        """
        if v is None or isinstance(v, LocalAccount):
            return v
        return Account.from_key(v)

    @field_validator("linked_signer")
    @classmethod
    def linked_signer_to_local_account(
        cls, v: Optional[Signer]
    ) -> Optional[LocalAccount]:
        """
        Validates and converts the linked_signer to a LocalAccount instance.

        Args:
            v (Optional[Signer]): The linked_signer instance or None.

        Returns:
            Optional[LocalAccount]: The LocalAccount instance or None.
        """
        if v is None or isinstance(v, LocalAccount):
            return v
        return Account.from_key(v)
