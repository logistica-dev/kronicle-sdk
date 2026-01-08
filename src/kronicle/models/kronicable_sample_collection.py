from collections.abc import Sequence
from typing import Any

from kronicle.models.iso_datetime import now, now_local
from kronicle.models.kronicable_sample import KronicableSample
from kronicle.models.kronicle_payload import KroniclePayload


class KronicableSampleCollection:
    """
    A collection of KronicableSample objects that can be converted into a
    single KroniclePayload for transmission to the Kronicle microservice.

    Ensures that all samples share the same schema and automatically merges
    their rows into a KroniclePayload.
    """

    base_payload: KroniclePayload
    samples: list[KronicableSample]

    def __init__(self, base_payload: KroniclePayload, sample_list: Sequence[KronicableSample] | None = None):
        """
        Initialize the collection with an optional initial list of samples.

        Parameters
        ----------
        base_payload : KroniclePayload
            The base payload providing channel metadata (channel_id, name, etc.).
        sample_list : list[KronicableSample] | None
            Optional initial samples to add to the collection.
        """
        self.base_payload = base_payload
        self.samples = list(sample_list) if sample_list else []
        self._schema: dict[str, str] | None = None

    def add_sample(self, sample: KronicableSample):
        """
        Add a single sample to the collection.

        Raises
        ------
        ValueError
            If the sample schema does not match the existing collection schema.
        """

        sample_schema = sample.channel_schema
        if self._schema is None:
            self._schema = sample_schema
        else:
            # Check compatibility
            if sample_schema != self._schema:
                raise ValueError(f"Sample schema mismatch: {sample_schema} != {self._schema}")
        self.samples.append(sample)

    def add_sample_list(self, sample_list: Sequence[KronicableSample]):
        """
        Add multiple samples to the collection at once.

        Parameters
        ----------
        sample_list : list[KronicableSample]
            List of samples to add.
        """
        for sample in sample_list:
            self.add_sample(sample)

    @property
    def rows(self) -> list[dict[str, Any]]:
        """
        Return the collection as a list of row dictionaries, one per sample.

        Raises
        ------
        ValueError
            If the collection schema is not set.
        """
        if not self.samples:
            return []

        if not self._schema:
            # Should never happen
            raise ValueError("No schema was provided")

        rows: list[dict[str, Any]] = []
        for metric in self.samples:
            row: dict[str, Any] = {}
            for name in self._schema.keys():
                row[name] = getattr(metric, name, None)
            rows.append(row)
        return rows

    def to_kronicle_payload(self) -> KroniclePayload:
        """
        Convert the collection into a single KroniclePayload.
        Each sample becomes a row; the payload uses the merged schema.

        Raises
        ------
        ValueError
            If the collection has no samples.
        """
        if not self.samples:
            raise ValueError("No sample to convert")
        if not self._schema:
            # Should never happen
            raise ValueError("No schema was provided")

        payload = KroniclePayload(
            **self.base_payload.model_dump(),
        )
        payload.rows = self.rows
        payload.channel_schema = self._schema
        return payload


if __name__ == "__main__":
    """
    Demonstration of KronicableSampleCollection usage.
    """
    from uuid import uuid4

    from kronicle.models.iso_datetime import IsoDateTime
    from kronicle.utils.log import log_d

    here = "Test KronicableSampleCollection"

    # -------------------------------
    # Example KronicableSample subclass
    # -------------------------------
    class TransferSample(KronicableSample):
        start_time: IsoDateTime
        end_time: IsoDateTime | None = None
        bytes_received: int = 0
        error: str | None = None

        @property
        def success(self) -> bool:
            return self.error is None

    # -------------------------------
    # Base payload
    # -------------------------------
    base_payload = KroniclePayload(
        channel_id=uuid4(),
        channel_name="transfer_channel",
        metadata={"unit": "bytes"},
    )

    # -------------------------------
    # Create sample collection
    # -------------------------------
    collection = KronicableSampleCollection(base_payload)

    # Add valid samples
    s1 = TransferSample(start_time=now_local(), bytes_received=1000)
    s2 = TransferSample(start_time=now_local(), bytes_received=2000, error="timeout")
    collection.add_sample_list([s1, s2])

    log_d(here, "Added samples:", collection.samples)
    log_d(here, "Collection rows:", collection.rows)

    # Convert to KroniclePayload
    payload = collection.to_kronicle_payload()
    log_d(here, "KroniclePayload:", payload)

    # -------------------------------
    # Test schema mismatch
    # -------------------------------
    class BadSample(KronicableSample):
        start_time: IsoDateTime
        end_time: IsoDateTime | None = None
        total_bytes: int = 0  # different field name
        error: str | None = None

    bad_sample = BadSample(start_time=now(), total_bytes=50)

    try:
        collection.add_sample(bad_sample)
    except ValueError as e:
        log_d(here, "Caught expected schema mismatch error:", e)

    # -------------------------------
    # Test empty collection
    # -------------------------------
    empty_collection = KronicableSampleCollection(base_payload)
    try:
        empty_payload = empty_collection.to_kronicle_payload()
    except ValueError as e:
        log_d(here, "Caught expected error on empty collection:", e)
