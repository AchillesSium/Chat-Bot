from typing import List, Dict, Tuple
from bisect import bisect_left, insort_left


def debug_printer(item="Nothing was given to log.", sign="#"):
    print()
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


def add_to_week_allocation(allocList: List, tmpAlloc) -> List:
    wasFound = False
    for i in range(len(allocList)):
        if allocList[i][0] is tmpAlloc[0]:
            tmp = list(allocList[i])
            tmp[1] += tmpAlloc[1]
            allocList[i] = tuple(tmp)
            if allocList[i][1] == 1.0:
                # If it turns out a week was full because of multiple pre-existing allocations,
                # remove that item.
                del allocList[i]
            wasFound = True
            break
    if not wasFound:
        insort_left(allocList, tmpAlloc)
    return allocList


def add_person_in_order(people: List, newPerson: Tuple) -> List:
    if not people:
        people.append(newPerson)
    else:
        for i in range(len(people)):
            if people[i][2][0] >= newPerson[2][0]:
                # If the new person is on the same week, or on an earlier week
                # debug_printer(people[i][2][1], "II")
                # debug_printer(newPerson[2][1], "@@@")
                if people[i][2][1] < newPerson[2][1]:
                    # Existing entry is more occupied than the new person.
                    # debug_printer("Continue", "CON")
                    continue
                else:
                    # debug_printer("Insert at " + str(i), "IN ")
                    # debug_printer(people[i], "¤")
                    # debug_printer(newPerson, "%")
                    people.insert(i, newPerson)
                    break  # After insertion, there is no need to loop through the list.
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
        # debug_printer("Person loop start", "111")
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
                    # debug_printer("got to allocation's yearWeek being lesser than param yearWeek", "Å")
                    # debug_printer(str(allocation["yearWeek"]) + ": " + str(allocation["percentage"]), "å")
                    if allocation["percentage"] < 100:
                        # Allocation is not completely taken.
                        # debug_printer("Got to 'percentage < 100'")
                        tmpAlloc = (
                            int(allocation["yearWeek"][-2:]),
                            float(allocation["percentage"]) / 100,
                        )
                        # debug_printer(tmpAlloc, "tmpA")
                        allocList = add_to_week_allocation(allocList, tmpAlloc)
                        debug_printer(allocList, str(person[0]) + " ")
            # debug_printer(allocList, "PersonAlloDone")
        else:
            # Subject had no allocations.
            # debug_printer(str([person[0]]) + " was not found", "*")
            # allocList.append((int(yearWeek[-2:]), 0.0,))
            insort_left(allocList, (int(yearWeek[-2:]), 0.0,))
            # debug_printer(allocList, str(person[0]) + " _ ")
            # debug_printer(person + tuple(allocList))
        # All allocations extracted for person
        if allocList:
            # Only persons for whom allocations were available.
            # debug_printer(allocList, str(person) + " # ")
            person = person + tuple(allocList)
            # debug_printer(allocList, str(person) + " $ ")
            # debug_printer(person, "per")
            # Add in the remaining people, who are preoccupied but who are otherwise qualified.
            # debug_printer(tmpList, "TIME")
            tmpList = add_person_in_order(tmpList, person)
        # debug_printer("Person-loop end", "00")
    # debug_printer(tmpList, "NED")
    print("NED" * 6)
    print("NED" * 6)
    for line in tmpList:
        print(line)
    print("NED" * 6)
    print("NED" * 6)
    print()
    return tmpList  # Return the sorted list.


if __name__ == "__main__":
    # For debugging

    print("Breakpoint here")
