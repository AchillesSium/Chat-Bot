from typing import List, Dict, Tuple
from bisect import bisect_left, insort_left


def debug_printer(item="Nothing was given to log.", sign="#"):
    """
    This function is for debugging purposes.
    :param item: item or message to be printed.
    :param sign: The character or string with which the message in this instance is highlighted.
    :return: None
    """
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

    At the end of its run, this function invokes sort_by_time,
    which sorts the matched people by time and discards unavailable people.

    :param skills: A list containing names of requested skills.
    :return: A List object containing found persons, sorted by their availability in time..
    """
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
                if requested_skill in person["skills"]:
                    # A match is found.
                    matching_person = person["employeeId"]
                    skillsTuple += (requested_skill,)  # Record the matched skill.
        if matching_person is not None:
            # At the end of the loop,
            # if a person with a matching skill has been found,
            # append him to the list which is to be returned.
            matching_people.append((matching_person, skillsTuple,))
    if len(matching_people) != 0:
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


def add_to_week_allocation(allocList: List, tmpAlloc) -> List:
    """
    This function is called during search when allocation are being attached to a person.
    It takes the list of allocations that a person is supposed to have
    and an allocation entry which is supposed to added in there,
    and then just adds it in.

    It also picks up on an allocation being added on to a week which already has an allocation.
    The code will add the preoccupation percentages together. If it then turns out, that the week
    is full, that week is determined to be unavailable and is promptly removed from the list.

    :param allocList: List of allocations for a person to which the new item is supposed to be allocated.
    :param tmpAlloc: The new allocation which is to be allocated into the list.
    :return: The list with the new item in the right place.
    """
    wasFound = False  # A flag for detecting whether an entry with the same week already existed.
    for i in range(len(allocList)):
        # Go through the list to find the appropriate index.
        if allocList[i][0] is tmpAlloc[0]:
            # A match is found where the new allocation and an existing allocation
            # take place on the same week.
            tmp = list(allocList[i])
            tmp[1] += tmpAlloc[1]
            allocList[i] = tuple(tmp)
            if allocList[i][1] == 1.0:
                # If it turns out a week was full because of multiple pre-existing allocations,
                # remove that item.
                del allocList[i]
            wasFound = True  # A match was found and handled.
            break  # After the match was handled, there is no further need to loop through the list.
    if not wasFound:
        # If the new item did not previously exist on the list, it is now added in.
        insort_left(allocList, tmpAlloc)
    return allocList


def add_person_in_order(people: List, newPerson: Tuple) -> List:
    """
    This function is invoked at the end of sort_by_time.
    It is used to add new people with their time allocations into the final
    list which is to be put out.

    :param people: The list to which the new person is to be added.
    :param newPerson: The new person to be added into the list.
    :return: The list with the new person added in.
    """
    if not people:
        # List is empty. Add the first item.
        people.append(newPerson)
    else:
        wasAdded = False  # A flag for detecting whether the new person could be added during the loop.
        for i in range(len(people)):
            # Loop through the list and add the new person to the appropriate position.
            # (731, ('C',), (('2020-W47', 0.0),))   # Format of a person on the list.
            if people[i][2][0][0] >= newPerson[2][0][0]:
                # If the new person is on the same week, or on an earlier week
                if people[i][2][0][1] >= newPerson[2][0][1]:
                    # Existing entry is more preoccupied than the new person.
                    people.insert(i, newPerson)
                    wasAdded = True
                    break  # After insertion, there is no need to loop through the list.
            else:
                # NOTE: this block might or might not be necessary.
                people.insert(i, newPerson)
                break  # After insertion, there is no need to loop through the list.
        if not wasAdded:
            # Person could not be added during the loop, so they will be added to the end of the list.
            people.append(newPerson)
    return people


def sort_by_time(matching_people: List, allocationsFile: List, yearWeek: str) -> List:
    """
    This function takes the list of all the people with the matching skills,
    looks to see if they have available time slots and adds those in order.

    :param matching_people: A list containing people whose skills matched the request.
    :param allocationsFile: The output of the allocations API represented as a Dict.
    :param yearWeek: The expected time for candidate to be available. The form is year-Wweek. For example, 2020-W32
    :return: list sorted with most available people at the top.
    """
    tmpList = []
    allocList = []
    for person in matching_people:
        # Cycle through all the people who were matched.
        allocList = []
        if person[0] in allocationsFile:
            for allocation in allocationsFile[person[0]]:
                # In the JSON structure of allocations, the base level units are divided
                # into two entities: "user" and "projects"
                if allocation["yearWeek"] >= yearWeek:
                    # Detect weeks equal or later than param yearWeek
                    if allocation["percentage"] < 100:
                        # Allocation is not completely taken.
                        tmpAlloc = (
                            allocation["yearWeek"],
                            float(allocation["percentage"]) / 100,
                        )
                        allocList = add_to_week_allocation(allocList, tmpAlloc)
                        if len(allocList) == 10:
                            break  # Ten entries is enough.
        else:
            # Subject had no allocations.
            insort_left(allocList, (yearWeek, 0.0,))
        # All allocations extracted for person
        if allocList:
            # Only persons for whom allocations were available.
            person = person + (tuple(allocList),)
            # Add in the remaining people, who are preoccupied but who are otherwise qualified.
            tmpList = add_person_in_order(tmpList, person)
    return tmpList  # Return the sorted list.


if __name__ == "__main__":
    # For debugging

    print("Breakpoint here")
