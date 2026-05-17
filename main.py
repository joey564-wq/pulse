def greet(name: str) -> str:
    return f"Hello, {name}!"


def main() -> None:
    print(greet("pulse"))
    print(greet("world"))


if __name__ == "__main__":
    main()