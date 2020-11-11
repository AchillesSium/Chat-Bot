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


def get_next_yearWeek(yearWeek: str) -> str:
    week = int(yearWeek[-2:])
    week += 1
    if week > 52:
        week = 0
        week = yearWeek[:-2] + "00"
    else:
        week = yearWeek[:-2] + str(week)
    return week


def get_time_comparison(employeeId, allocations: List, yearWeek: str):
    None


def sort_by_time(matching_people: List, allocations: List, yearWeek: str) -> List:
    """

    :param matching_people:
    :param yearWeek: The expected time for candidate to be available. The form is year-Wweek. For example, 2020-W32
    :return: list sorted as most available people at the top.
    """
    tmpList = []
    for person in matching_people:
        # Cycle through all the people who were matched.
        for unit in allocations:
            # In the JSON structure of allocations, the base level units are divided
            # into two entities: "user" and "projects"
            if person[0] is unit["user"]["id"]:
                # When we find a
                if yearWeek not in unit["project"]["allocations"]:
                    # The person in question is not involved in a project on the requested week.
                    tmpList.append(person)
    # Add in the remaining people, who are preoccupied but who are otherwise qualified.
    for person in matching_people:
        if person not in tmpList:
            tmpList.append(person)
    return tmpList  # Return the sorted list.

    return matching_people


if __name__ == "__main__":
    # For debugging

    print("Breakpoint here")
