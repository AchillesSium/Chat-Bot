import pytest

from bot.searches import find_kit

SOME_WEEK = "2020-W01"


def sample_users_with(employee_id, skills):
    sample_users = {i: {"employeeId": i, "skills": [f"skill {i}"]} for i in (1, 2, 3)}
    sample_users[employee_id] = {"employeeId": employee_id, "skills": skills}
    return sample_users


def test_person_with_matching_skills_is_found():
    employee_id = 0
    skills = ["matching skill"]
    users = sample_users_with(employee_id, skills)
    found = find_kit.find_person_by_skills(skills, users, {}, SOME_WEEK)
    assert len(found) == 1
    [(found_id, found_skills, _)] = found
    assert found_id == employee_id, "wrong person"
    assert set(found_skills) == set(skills), "wrong skill set"


def test_all_matching_skills_are_found():
    employee_id = 0
    skills = ["matching skill", "another", "one more"]
    users = sample_users_with(employee_id, skills)
    found = find_kit.find_person_by_skills(
        skills + ["not matching"], users, {}, SOME_WEEK
    )
    assert len(found) == 1
    [(_, found_skills, _)] = found
    assert set(found_skills) == set(skills), "wrong skill set"


@pytest.mark.parametrize(
    "percentages", ((100,), (20, 80), (80, 20), (100, 20), (20, 100))
)
def test_person_with_100_percent_allocation_is_excluded(percentages):
    assert sum(percentages) >= 100, "bad test data"
    employee_id = 0
    skills = ["matching skill"]
    allocation = {
        employee_id: [{"yearWeek": SOME_WEEK, "percentage": p} for p in percentages]
    }
    users = sample_users_with(employee_id, skills)
    found = find_kit.find_person_by_skills(skills, users, allocation, SOME_WEEK)
    assert not found
