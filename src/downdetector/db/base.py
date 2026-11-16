from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def sql_in(column: str, values: tuple[str, ...]) -> str:
    listed = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({listed})"
