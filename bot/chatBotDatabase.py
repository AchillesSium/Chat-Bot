import sqlite3
import datetime
import threading


class BotDatabase:
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, db_file_name: str):
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(db_file_name, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute(
                "CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY UNIQUE, employeeId INT)"
            )
            botdb.execute(
                "CREATE TABLE IF NOT EXISTS history(user_id TEXT, dateStamp TEXT, recommended_skill TEXT, FOREIGN KEY(user_id) REFERENCES users(id))"
            )

    def add_user(self, user_id, employee_id):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            try:
                botdb.execute(
                    "INSERT INTO users (id, employeeId) VALUES(?,?)",
                    (user_id, employee_id),
                )
            except sqlite3.IntegrityError:
                raise KeyError("User already exists")

    def add_history(self, user_id, dateStamp, recommended_skill):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            dateStamp = dateStamp.strftime(self.DATE_FORMAT)
            botdb.execute(
                "INSERT OR IGNORE INTO history (user_id, dateStamp, recommended_skill) VALUES(?,?,?)",
                (user_id, dateStamp, recommended_skill),
            )

    def get_user_by_id(self, user_id):
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM users WHERE id = (?)", (user_id,))
        result = botdb.fetchall()
        if not result:
            raise KeyError("user_id not found", user_id)
        assert len(result) == 1, "database is corrupt"
        return result[0]

    def get_user_by_employeeid(self, employee_id):
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM users WHERE employeeId = (?)", (employee_id,))
        return botdb.fetchall()

    def get_users(self):
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM users")
        return botdb.fetchall()

    def _parse_history(self, history):
        # TODO: use adapters and converters for datetime.datetime instead
        return [
            (a, datetime.datetime.strptime(date, self.DATE_FORMAT), c)
            for a, date, c in history
        ]

    def get_history_by_user_id(self, user_id):
        botdb = self.connection.cursor()
        botdb.execute(
            "SELECT * FROM history WHERE user_id = (?) ORDER BY dateStamp DESC",
            (user_id,),
        )
        return self._parse_history(botdb.fetchall())

    def get_history_sortedby_datestamp(self):
        botdb = self.connection.cursor()
        botdb.execute("SELECT * FROM history ORDER BY dateStamp DESC")
        return self._parse_history(botdb.fetchall())

    def delete_user(self, user_id):
        self.get_user_by_id(user_id)  # fail if user does not exist
        self.delete_history_by_user_id(user_id)
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute("DELETE FROM users WHERE user_id = (?)", (user_id,))

    def delete_history_by_user_id(self, user_id):
        with self._lock, self.connection as conn:
            botdb = conn.cursor()
            botdb.execute("DELETE FROM history WHERE user_id = (?)", (user_id,))

    def close(self):
        self.connection.close()
