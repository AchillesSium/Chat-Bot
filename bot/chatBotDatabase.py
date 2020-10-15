import sqlite3
import datetime

class BotDatabase:

    def __init__(self, db_file_name):
        db_file_name = str(db_file_name)
        self.dbConnetion = sqlite3.connect(db_file_name)
        self.create_tables()

    def create_tables(self):
        self.create_users_table()
        self.create_history_table()

    def create_users_table(self):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            botdb.execute('CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY UNIQUE, employeeId INT)')

    def create_history_table(self):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            botdb.execute('CREATE TABLE IF NOT EXISTS history(user_id TEXT, dateStamp TEXT, recomended_team TEXT, FOREIGN KEY(user_id) REFERENCES users(id))')

    def add_users(self, id, employeeId):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            id  = str(id)
            employeeId = int(employeeId)
            try:
                botdb.execute("INSERT INTO users (id, employeeId) VALUES(?,?)",
                    (id, employeeId))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
                # raise KeyError('User already exists')

    def add_history(self, user_id, dateStamp, recomended_team):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            user_id = str(user_id)
            dateStamp = dateStamp.strftime('%Y-%m-%d %H:%M:%s')
            recomended_team = str(recomended_team)
            try:
                botdb.execute("INSERT OR IGNORE INTO history (user_id, dateStamp, recomended_team) VALUES(?,?,?)",
                (user_id, dateStamp, recomended_team))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_user_by_id(self, id):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            id = str(id)
            botdb.execute("SELECT * FROM users WHERE id = (?)", (id,))
            return botdb.fetchall()

    def get_user_by_employeeid(self, employeeId):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            employeeId = str(employeeId)
            botdb.execute("SELECT * FROM users WHERE employeeId = (?)", (employeeId,))
            return botdb.fetchall()

    def get_history_by_user_id(self, user_id):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            user_id = str(user_id)
            botdb.execute("SELECT * FROM history WHERE user_id = (?)", (user_id,))
            return botdb.fetchall()

    def get_history_sortedby_datestamp(self):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            botdb.execute("SELECT * FROM history ORDER BY dateStamp DESC")
            return botdb.fetchall()

    def get_history_by_recommendedTeam(self, recomended_team):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            recomended_team = str(recomended_team)
            botdb.execute("SELECT * FROM history WHERE recomended_team = (?)", (recomended_team,))
            return botdb.fetchall()

    def delete_history_by_user_Id(self, user_id):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            user_id = str(user_id)
            try:
                botdb.execute("DELETE FROM history WHERE user_id = (?)", (user_id,))
                conn.commit()
                return True
            except:
                print('False')
                return False

    def close_database(self):
        with self.dbConnetion as conn:
            botdb = conn.cursor()
            botdb.close()
            conn.close()
