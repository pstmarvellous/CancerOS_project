from canceros.jobs import dispatch, process_one, queue_for, recover
from canceros.persistence import engine_for
from canceros.settings import Settings
from canceros.storage import PrivateStorage


def main():
    settings = Settings()
    engine = engine_for(settings)
    queue = queue_for(settings)
    recover(engine, queue)
    dispatch(engine, queue)
    storage = PrivateStorage(settings)
    count = 0
    for _ in range(25):
        if process_one(engine, queue, storage, settings) is None:
            break
        count += 1
    print(
        f"Engineering-only worker: processed {count} transport entries; SQL records authoritative status"
    )
    engine.dispose()


if __name__ == "__main__":
    main()
