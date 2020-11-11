def find_person_by_skills(self, skills: List[str], users: dict = None):
    """Look for people with a certain set of skills.

    :param skills: A list containing names of requested skills.
    :return: A List object containing found persons.
    """
    # Go through bot's database for people.
    if users == None:
        # Error
        # TODO: Put an error message here.
        pass
    matching_people = []
    for person in users.values():
        # Go through all the people in the API
        matching_person = []  # Holds worker_id and matched skills.
        for requested_skill in skills:
            # Look for matches in list of requested skills.
            # TODO: use fuzzier matching, not equality (==)
            if requested_skill in person["skills"]:
                # A match is found.
                if len(matching_person) == 0:
                    # Person with a matching skill gets detected for the first time.
                    matching_person.append(person["employeeId"])
                matching_person.append(requested_skill)  # Record the matched skill.
        if len(matching_person) != 0:
            # At the end of the loop,
            # if a person with a matching skill has been found,
            # append him to the list which is to be returned.
            matching_people.append(matching_person)

    return matching_people


def sort_by_time(matching_people: List, yearWeek: str) -> List:
    """

    :param matching_people:
    :param yearWeek: form is year-Wweek. For example, 2020-W32
    :return: list sorted as most available people at the top.
    """
    pass
    tmpList = []

    return matching_people


if __name__ == "__main__":
    # For debugging

    print("Breakpoint here")
