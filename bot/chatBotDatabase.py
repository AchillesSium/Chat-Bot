import sqlite3
import datetime
import threading

import psycopg2 as psy

from typing import NamedTuple, Optional, List, Tuple, Dict


class User(NamedTuple):
    user_id: str
    employee_id: int
    remind_next: Optional[datetime.datetime] = None


HistoryEntry = Tuple[str, datetime.datetime, str]


class IBotDatabase:
    def add_user(self, user: User) -> None:
        ...

    def set_next_reminder(self, user_id: str, at: datetime.datetime) -> None:
        ...

    def add_history(
        self, user_id: str, dateStamp: datetime.datetime, recommended_skill: str
    ) -> None:
        ...

    def get_user_by_id(self, user_id: str) -> User:
        ...

    def get_user_by_employeeid(self, employee_id: int) -> List[User]:
        ...

    def get_users(self) -> List[User]:
        ...

    def get_history_by_user_id(self, user_id: str) -> List[HistoryEntry]:
        ...

    def get_history_sortedby_datestamp(self) -> List[HistoryEntry]:
        ...

    def delete_user(self, user_id: str) -> None:
        ...

    def delete_history_by_user_id(self, user_id: str) -> None:
        ...

    def close(self) -> None:
        ...


class SQLiteBotDatabase(IBotDatabase):
    def __init__(self, db_file_name: str):
        self._lock = threading.RLock()
        FLAGS = sqlite3.PARSE_COLNAMES | sqlite3.PARSE_DECLTYPES
        self.connection = sqlite3.connect(
            db_file_name, check_same_thread=False, detect_types=FLAGS
        )
        self._create_tables()

    def _create_tables(self):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute(
                "CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY UNIQUE, employeeId INT UNIQUE NOT NULL, remind_next timestamp)"
            )
            botdb.execute(
                "CREATE TABLE IF NOT EXISTS history(user_id TEXT, dateStamp timestamp, recommended_skill TEXT, FOREIGN KEY(user_id) REFERENCES users(id))"
            )

    def add_user(self, user: User):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            try:
                botdb.execute("INSERT INTO users VALUES(?,?,?)", user)
            except sqlite3.IntegrityError:
                raise KeyError("User already exists")

    def set_next_reminder(self, user_id: str, at: datetime.datetime):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute(
                "UPDATE users SET remind_next = (?) WHERE id = (?)", (at, user_id)
            )
            if botdb.rowcount != 1:
                raise KeyError("User does not exist")

    def add_history(self, user_id, dateStamp, recommended_skill):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute(
                "INSERT OR IGNORE INTO history (user_id, dateStamp, recommended_skill) VALUES(?,?,?)",
                (user_id, dateStamp, recommended_skill),
            )

    def get_user_by_id(self, user_id: str) -> User:
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM users WHERE id = (?)", (user_id,))
        result = botdb.fetchall()
        if not result:
            raise KeyError("user_id not found", user_id)
        assert len(result) == 1, "database is corrupt"
        return User(*result[0])

    def get_user_by_employeeid(self, employee_id: int) -> List[User]:
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM users WHERE employeeId = (?)", (employee_id,))
        return [User(*row) for row in botdb.fetchall()]

    def get_users(self) -> List[User]:
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM users")
        return [User(*row) for row in botdb.fetchall()]

    def get_history_by_user_id(self, user_id: str) -> List[HistoryEntry]:
        botdb = self.connection.cursor()
        botdb.execute(
            "SELECT * FROM history WHERE user_id = (?) ORDER BY dateStamp DESC",
            (user_id,),
        )
        return botdb.fetchall()

    def get_history_sortedby_datestamp(self) -> List[HistoryEntry]:
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM history ORDER BY dateStamp DESC")
        return botdb.fetchall()

    def delete_user(self, user_id):
        self.get_user_by_id(user_id)  # fail if user does not exist
        self.delete_history_by_user_id(user_id)
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute("DELETE FROM users WHERE id = (?)", (user_id,))

    def delete_history_by_user_id(self, user_id):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute("DELETE FROM history WHERE user_id = (?)", (user_id,))

    def close(self):
        self.connection.close()


class PostgresBotDatabase(IBotDatabase):
    def __init__(self, connection_string: str):
        self._lock = threading.RLock()

        self.connection = psy.connect(connection_string)
        self._create_tables()

    def __del__(self):
        self.connection.close()

    def _create_tables(self):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute(
                "CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY UNIQUE, employeeId INT UNIQUE NOT NULL, remind_next timestamp)"
            )

        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute(
                "CREATE TABLE IF NOT EXISTS history(user_id TEXT, dateStamp timestamp, recommended_skill TEXT, FOREIGN KEY(user_id) REFERENCES users(id))"
            )

    def add_user(self, user: User):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            try:
                botdb.execute("INSERT INTO users VALUES(%s,%s,%s)", user)
            except psy.errors.UniqueViolation:
                raise KeyError("User already exists")

    def set_next_reminder(self, user_id: str, at: datetime.datetime):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute(
                "UPDATE users SET remind_next = %s WHERE id = %s", (at, user_id)
            )
            if botdb.rowcount != 1:
                raise KeyError("User does not exist")

    def add_history(self, user_id, dateStamp, recommended_skill):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            try:
                botdb.execute(
                    "INSERT INTO history (user_id, dateStamp, recommended_skill) VALUES(%s,%s,%s)",
                    (user_id, dateStamp, recommended_skill),
                )
            except psy.errors.ForeignKeyViolation:
                pass

    def get_user_by_id(self, user_id: str) -> User:
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        result = botdb.fetchall()
        if not result:
            raise KeyError("user_id not found", user_id)
        assert len(result) == 1, "database is corrupt"
        return User(*result[0])

    def get_user_by_employeeid(self, employee_id: int) -> List[User]:
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM users WHERE employeeId = %s", (employee_id,))
        return [User(*row) for row in botdb.fetchall()]

    def get_users(self) -> List[User]:
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM users")
        return [User(*row) for row in botdb.fetchall()]

    def get_history_by_user_id(self, user_id: str) -> List[HistoryEntry]:
        botdb = self.connection.cursor()
        botdb.execute(
            "SELECT * FROM history WHERE user_id = %s ORDER BY dateStamp DESC",
            (user_id,),
        )
        return botdb.fetchall()

    def get_history_sortedby_datestamp(self) -> List[HistoryEntry]:
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM history ORDER BY dateStamp DESC")
        return botdb.fetchall()

    def delete_user(self, user_id):
        self.get_user_by_id(user_id)  # fail if user does not exist
        self.delete_history_by_user_id(user_id)
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute("DELETE FROM users WHERE id = %s", (user_id,))

    def delete_history_by_user_id(self, user_id):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute("DELETE FROM history WHERE user_id = %s", (user_id,))

    def close(self):
        self.connection.close()


def get_database_object(
    db_type: Optional[str] = None, parameters: Optional[Dict[str, str]] = None
) -> IBotDatabase:
    """ Get the correct database object with the given type and parameters

    Parameters for sqlite database should contain the key "sqlite_db_file".
        E.g. {"sqlite_db_file": ":memory:"}

    Parameters for postgres database should contain the key "postgres_connection_string".
        E.g. {"postgres_connection_string": "dbname=chatbotdb user=postgres password=postgres"}

    :param db_type: Postgre or sqlite
    :param parameters: Connection parameters.
    :return: Database object
    """
    if db_type is None:
        db_type = "sqlite"

    if parameters is None:
        parameters = {
            "sqlite_db_file": ":memory:",
            "postgres_connection_string": "dbname=chatbotdb user=postgres password=postgres",
        }

    db_type = db_type.lower()

    db_dict = {
        "postgre": lambda: PostgresBotDatabase(
            parameters["postgres_connection_string"]
        ),
        "sqlite": lambda: SQLiteBotDatabase(parameters["sqlite_db_file"]),
    }

    for t, db_lambda in db_dict.items():
        if db_type.startswith(t):
            db = db_lambda()
            break
    else:
        # I think this is better than a default db_type
        raise AttributeError(
            f"Unknown database type {db_type}.\nKnown types: postgre, sqlite"
        )

    return db
