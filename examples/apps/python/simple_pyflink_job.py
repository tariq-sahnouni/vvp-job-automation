import time

from pyflink.common import Types
from pyflink.datastream import StreamExecutionEnvironment


def format_event(value: int) -> str:
    time.sleep(1)
    return f"VVP template event {value}"


def main() -> None:
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    numbers = env.from_collection(range(1, 301), type_info=Types.INT())
    messages = numbers.map(
        format_event,
        output_type=Types.STRING(),
    )
    messages.print()
    env.execute("vvp-template-python-example")


if __name__ == "__main__":
    main()
