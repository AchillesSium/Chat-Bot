from typing import List, Dict, Tuple
from bisect import bisect_left


def debug_printer(item="Nothing was given to log.", sign="#"):
    print(sign * 6)
    print(sign * 6)
    print(item)
    print(sign * 6)
    print(sign * 6)


def yearWeek_string_to_tuple(yearWeek: str) -> Tuple:
    return (int(yearWeek[:4]), int(yearWeek[-2:]))


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
                # debug_printer(requested_skill, "¤")
                # debug_printer("This person has skills.")
                if requested_skill in person["skills"]:
                    # A match is found.
                    # if len(matching_person) == 0:
                    # Person with a matching skill gets detected for the first time.
                    # debug_printer("Requested skill found: " + requested_skill)
                    matching_person = person["employeeId"]
                    # matching_person.append(requested_skill)
                    skillsTuple += (requested_skill,)  # Record the matched skill.
        if matching_person is not None:
            # At the end of the loop,
            # if a person with a matching skill has been found,
            # append him to the list which is to be returned.
            matching_people.append((matching_person, skillsTuple,))
    # Check out the allocations for all found people.
    # debug_printer(len(matching_people), "@")
    if len(matching_people) != 0:
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
    if people:
        for i in range(len(people)):
            # debug_printer(people[i], "¤")
            # debug_printer(newPerson, "%")
            try:
                if not people[i][2]:
                    # Find a person who had an allocation but it was full.
                    del people[i]
                    continue
                if people[i][2][0] > newPerson[2][0]:
                    if people[i][2][1] > newPerson[2][1]:
                        people.insert(i, newPerson)
                    else:
                        continue
                    break
            except IndexError:
                pass
    else:
        people.append(newPerson)
    return people


def sort_by_time(matching_people: List, allocationsFile: List, yearWeek: str) -> List:
    """

    :param matching_people:
    :param yearWeek: The expected time for candidate to be available. The form is year-Wweek. For example, 2020-W32
    :return: list sorted as most available people at the top.
    """
    tmpList = []
    allocList = []
    # debug_printer(matching_people, "MM")
    for person in matching_people:
        # Cycle through all the people who were matched.
        allocList = []
        if person[0] in allocationsFile:
            # debug_printer(allocationsFile[person[0]], "ALLO")
            for allocation in allocationsFile[person[0]]:
                # In the JSON structure of allocations, the base level units are divided
                # into two entities: "user" and "projects"
                # debug_printer(person, "%")
                # debug_printer(allocation, "&")
                if allocation["yearWeek"] >= yearWeek:
                    # Detect weeks equal or later than param yearWeek
                    if allocation["percentage"] < 100:
                        # Allocation is not completely taken.
                        tmpAlloc = (
                            int(allocation["yearWeek"][-2:]),
                            float(allocation["percentage"]) / 100,
                        )
                        allocList.insert(bisect_left(allocList, tmpAlloc), tmpAlloc)
        else:
            # Subject had no allocations.
            # debug_printer(str([person[0]]) + " was not found", "*")
            allocList.append((int(yearWeek[-2:]), 0.0,))
            # debug_printer(person + tuple(allocList))
        # All allocations extracted for person
        person = person + tuple(allocList)
        # Add in the remaining people, who are preoccupied but who are otherwise qualified.
        debug_printer(tmpList, "TIME")
        tmpList = add_person_in_order(tmpList, person)
    debug_printer(tmpList, "NED")
    return tmpList  # Return the sorted list.


if __name__ == "__main__":
    # For debugging

    print("Breakpoint here")
