import tempfile
import unittest
import zipfile
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from adapters.artifacts.local_store import LocalArtifactStore
from core.domain.planning import DeliverableFile, TaskDeliverable


class DeliverableValidationTests(unittest.TestCase):
    def test_rejects_parent_directory_traversal(self) -> None:
        with self.assertRaises(ValidationError):
            DeliverableFile(path="../secret", content="nope")

    def test_accepts_structured_validation_commands(self) -> None:
        deliverable = TaskDeliverable(
            summary="Implemented and tested",
            files=[DeliverableFile(path="src/app.py", content="print('ok')")],
            validation_commands=[["python", "-m", "compileall", "."]],
        )
        self.assertEqual(deliverable.files[0].path, "src/app.py")


class ArtifactStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_materializes_hashes_and_bundles_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalArtifactStore(directory)
            project_id = uuid4()
            work_item_id = uuid4()
            await store.materialize(project_id, "src/app.py", b"print('ok')\n")
            stored = await store.put(
                project_id, work_item_id, "src/app.py", b"print('ok')\n"
            )
            self.assertEqual(
                await store.get(stored.storage_reference, stored.content_hash),
                b"print('ok')\n",
            )

            bundle = await store.bundle(project_id, work_item_id)
            self.assertIsNotNone(bundle)
            assert bundle is not None
            archive_path = Path(directory) / bundle.storage_reference
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(archive.namelist(), ["src/app.py"])
                self.assertEqual(archive.read("src/app.py"), b"print('ok')\n")

    async def test_rejects_unsafe_materialized_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalArtifactStore(directory)
            with self.assertRaises(ValueError):
                await store.materialize(uuid4(), "../../escape", b"nope")
