import argparse

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL

from reusable_helpers.shared.config import UNSET, resolve


def run_migrations(
    *,
    config=UNSET,
    revision=UNSET,
    host=UNSET,
    port=UNSET,
    user=UNSET,
    password=UNSET,
    database=UNSET,
    driver=UNSET,
):
    url = URL.create(
        resolve(driver, env="ALEMBIC_DRIVER", default="postgresql+psycopg2"),
        username=resolve(user, env="PGUSER", required=True),
        password=resolve(password, env="PGPASSWORD", required=True),
        host=resolve(host, env="PGHOST", required=True),
        port=resolve(port, env="PGPORT", default=5432, parser=int),
        database=resolve(database, env="PGDATABASE", required=True),
    )
    cfg = Config(resolve(config, env="ALEMBIC_CONFIG", default="alembic.ini"))
    # ConfigParser treats % specially, including URL-escaped credentials.
    cfg.set_main_option(
        "sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%")
    )
    command.upgrade(cfg, resolve(revision, env="ALEMBIC_REVISION", default="head"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in (
        "config",
        "revision",
        "host",
        "user",
        "password",
        "database",
        "driver",
    ):
        parser.add_argument(f"--{field}", default=UNSET)
    parser.add_argument("--port", type=int, default=UNSET)
    run_migrations(**vars(parser.parse_args()))


if __name__ == "__main__":
    main()
