from bot.chatBotDatabase import get_database_object, User


def get_sqlite(in_memory: bool):
    db_name = ":memory:" if in_memory else "db_name.db"
    return get_database_object("sqlite", db_name)


def test_in_memory():
    db = get_sqlite(True)

    test_user = User("ASDF", 1234)

    db.add_user(test_user)

    assert test_user == db.get_user_by_id(
        test_user.user_id
    ), "User is stored correctly in database"
