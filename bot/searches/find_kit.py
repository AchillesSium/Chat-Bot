from typing import List, Dict, Tuple
from bisect import bisect_left


def debug_printer(item="Nothing was given to log.", sign="#"):
    print(sign * 6)
    print(sign * 6)
    print(item)
    print(sign * 6)
    print(sign * 6)


def find_person_by_skills(
    skills: List[str], users: Dict, allocations: Dict, yearWeek: str
):
    """Look for people with a certain set of skills.

    :param skills: A list containing names of requested skills.
    :return: A List object containing found persons.
    """
    # Go through bot's database for people.
    matching_people = []
    skillsTuple = ()
    for person in users.values():
        # Go through all the people in the API
        matching_person = None  # Holds worker_id and matched skills.
        skillsTuple = ()  # Tuple for holding the skills.
        for requested_skill in skills:
            # Look for matches in list of requested skills.
            if person["skills"] is not None:
                # Check to see if person has skills at all.
                debug_printer(requested_skill, "¤")
                # debug_printer("This person has skills.")
                if requested_skill in person["skills"]:
                    # A match is found.
                    # if len(matching_person) == 0:
                    # Person with a matching skill gets detected for the first time.
                    debug_printer("Requested skill found: " + requested_skill)
                    matching_person = person["employeeId"]
                    # matching_person.append(requested_skill)
                    skillsTuple += (requested_skill,)  # Record the matched skill.
        if matching_person is not None:
            # At the end of the loop,
            # if a person with a matching skill has been found,
            # append him to the list which is to be returned.
            matching_people.append((matching_person, skillsTuple))
        # Check out the allocations for all found people.
        matching_people = sort_by_time(matching_people, allocations, yearWeek)

    return matching_people


def get_next_yearWeek(yearWeek: str) -> str:
    week = int(yearWeek[-2:])
    week += 1
    if week > 53:
        week = 0
        week = yearWeek[:-2] + "00"
    else:
        week = yearWeek[:-2] + str(week)
    return week


def add_person_in_order(people: List, newPerson: Tuple) -> List:
    for i in range(people):
        if people[i][2][0][0] > newPerson[2][0][0]:
            people.insert(i, newPerson)
            break
    return people


def sort_by_time(matching_people: List, allocations: List, yearWeek: str) -> List:
    """

    :param matching_people:
    :param yearWeek: The expected time for candidate to be available. The form is year-Wweek. For example, 2020-W32
    :return: list sorted as most available people at the top.
    """
    tmpList = []
    allocList = []
    for person in matching_people:
        # Cycle through all the people who were matched.
        allocList = []
        for unit in allocations:
            # In the JSON structure of allocations, the base level units are divided
            # into two entities: "user" and "projects"
            if person[0] is unit["user"]["employeeId"]:
                # Find a person's block in the system
                for alloc in unit["projects"]["allocations"]:
                    if alloc["yearWeek"] >= yearWeek:
                        # Detect weeks equal or later than param yearWeek
                        if alloc["percentage"] < 100:
                            # Allocation is not completely taken.
                            tmpAlloc = (
                                int(alloc["yearWeek"][-2:]),
                                float(alloc["percentage"]) / 100,
                            )
                            allocList.insert(bisect_left(allocList, tmpAlloc), tmpAlloc)
        # All allocations extracted for person
        person = person + tuple(allocList)
        # Add in the remaining people, who are preoccupied but who are otherwise qualified.
        tmpList = add_person_in_order(tmpList, person)
    # tmpList = sorted(matching_people, key=get_time_comparison(matching_people, allocations, yearWeek))
    return tmpList  # Return the sorted list.


if __name__ == "__main__":
    # For debugging

    print("Breakpoint here")
