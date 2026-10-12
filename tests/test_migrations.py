import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from sqlalchemy.engine import make_url

    from scripts.run_migrations import run_migrations
except ImportError:
    MIGRATION_DEPENDENCIES = False
else:
    MIGRATION_DEPENDENCIES = True


@unittest.skipUnless(MIGRATION_DEPENDENCIES, "migration dependencies not installed")
class MigrationTests(unittest.TestCase):
    def test_credentials_stay_in_memory_and_explicit_host_overrides_env(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alembic.ini"
            original = "[alembic]\nscript_location = migrations\n"
            path.write_text(original)
            with patch.dict(os.environ, {"PGHOST": "environment-host"}):
                with patch("scripts.run_migrations.command.upgrade") as upgrade:
                    run_migrations(
                        config=str(path),
                        host="explicit-host",
                        user="example",
                        password="example@password:%",
                        database="example",
                        revision="head",
                    )
            config, revision = upgrade.call_args.args
            url = make_url(config.get_main_option("sqlalchemy.url"))
            self.assertEqual(url.host, "explicit-host")
            self.assertEqual(url.password, "example@password:%")
            self.assertEqual(revision, "head")
            self.assertEqual(path.read_text(), original)


if __name__ == "__main__":
    unittest.main()
