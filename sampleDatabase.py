import sqlite3
import random
import  time

conn = sqlite3.connect('botdb.db')
c = conn.cursor()

def create_table():
    c.execute('CREATE TABLE IF NOT EXISTS employees(id INT UNIQUE, name TEXT, designation TEXT, joiningDate TEXT, skill REAL)')

def dynamic_data():
    empid = input('What is your employee id?\n')
    name = input('Please enter your name\n')
    designation = input('Designation: \n')
    joinningdate = input('You joining date? (dd-mm-yyyy):\n')
    skill = random.randrange(5,10)
    c.execute("INSERT OR IGNORE INTO employees (id, name, designation, joiningDate, skill) VALUES(?,?,?,?,?)",
                  (empid, name, designation, joinningdate, skill))
    conn.commit()

def search_for_empid():
    empid = input('Type your employee id to search?\n')
    c.execute("SELECT * FROM employees WHERE id = (?)", (empid))
    print(c.fetchall())

def update_designation():
    empid = input('What is your employee id?\n')
    designation = input('Designation: \n')
    c.execute("UPDATE employees SET designation = (?) WHERE id = (?)", (designation,empid))
    conn.commit()
    c.execute("SELECT * FROM employees WHERE id=" + empid)
    print(c.fetchall())

def delete_row():
    empid = input('Type employee id to delete:\n')
    c.execute("DELETE FROM employees WHERE id=" + empid)
    conn.commit()
    c.execute("SELECT * FROM employees")
    for row in c.fetchall():
        print(row)

create_table()

for i in range(2):
    dynamic_data()


search_for_empid()
update_designation()
delete_row()

c.close()
conn.close()