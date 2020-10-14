import sqlite3

dbConnetion = sqlite3.connect('chatbotDB.db')
db = dbConnetion.cursor()

def create_tables():
    create_users_table()
    create_history_table()

def create_users_table():
    db.execute('CREATE TABLE IF NOT EXISTS users(id INT PRIMARY KEY UNIQUE, employeeId INT)')

def create_history_table():
    db.execute('CREATE TABLE IF NOT EXISTS history(user_id INT UNIQUE, dateStamp TEXT, recomended_team TEXT, FOREIGN KEY(user_id) REFERENCES users(id))')

def insert_data_to_users_table(id, employeeId):
    id  = int(id)
    employeeId = int(id)
    db.execute("INSERT OR IGNORE INTO users (id, employeeId) VALUES(?,?)",
             (id, employeeId))
    dbConnetion.commit()

def insert_data_to_history_table(user_id, dateStamp, recomended_team):
    user_id = int(user_id)
    dateStamp = str(dateStamp)
    recomended_team = str(recomended_team)
    db.execute("INSERT OR IGNORE INTO history (user_id, dateStamp, recomended_team) VALUES(?,?,?)",
             (user_id, dateStamp, recomended_team))
    dbConnetion.commit()

def getLastIdNumber():
    db.execute("SELECT id FROM users WHERE id = (SELECT MAX(id) FROM users)")
    lastid = 1
    data = db.fetchall()
    if len(data) > 0:
        lastid = data[0]
        lastid = lastid[0]
    return lastid

def getUserById(id):
    id = str(id)
    db.execute("SELECT * FROM users WHERE id = (?)", (id,))
    return db.fetchall()

def getUserByemployeeId(employeeId):
    employeeId = str(employeeId)
    db.execute("SELECT * FROM users WHERE employeeId = (?)", (employeeId,))
    return db.fetchall()

def getHistoryByUser_Id(user_id):
    user_id = str(user_id)
    db.execute("SELECT * FROM history WHERE user_id = (?)", (user_id,))
    return db.fetchall()

def getHistoryByDatestamp(datestamp):
    datestamp = str(datestamp)
    db.execute("SELECT * FROM history WHERE user_id = (?)", (datestamp,))
    return db.fetchall()

def getHistoryByDatestamp(datestamp):
    datestamp = str(datestamp)
    db.execute("SELECT * FROM history WHERE dateStamp = (?)", (datestamp,))
    return db.fetchall()

def getHistoryByRecommendedTeam(recomended_team):
    recomended_team = str(recomended_team)
    db.execute("SELECT * FROM history WHERE recomended_team = (?)", (recomended_team,))
    return db.fetchall()

def updateHistoyByDateStamp(user_id, datestamp):
    datestamp = str(datestamp)
    user_id = str(user_id)
    db.execute("UPDATE history SET datestamp = (?) WHERE user_id = (?)", (datestamp, user_id))
    dbConnetion.commit()

def updateHistoyByRecommendedTeam(user_id, recomended_team):
    recomended_team = str(recomended_team)
    user_id = str(user_id)
    db.execute("UPDATE history SET recomended_team = (?) WHERE user_id = (?)", (recomended_team, user_id))
    dbConnetion.commit()

def deleteHistoryByUser_Id(user_id):
    user_id = str(user_id)
    db.execute("DELETE FROM history WHERE user_id =" + user_id)
    dbConnetion.commit()

def closeDatabase():
    db.close()
    dbConnetion.close()