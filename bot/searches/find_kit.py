from typing import List, Dict, Tuple
from bisect import insort_left


def find_person_by_skills(
    skills: List[str], users: Dict, allocations: Dict, year_week: str
):
    """Look for people with a certain set of skills.

    At the end of its run, this function invokes sort_by_time,
    which sorts the matched people by time and discards unavailable people.

    :param skills: A list containing names of requested skills.
    :param users: User information output of the Data API.
    :param allocations: Allocation information output of the Data API.
    :param year_week: The week for which available workers are being searched for.
    :return: A List object containing found persons, sorted by their availability in time..
    """
    matching_people = []
    for person in users.values():
        # Go through all the people in the API
        matching_person = None  # Holds worker_id and matched skills.
        skills_tuple = ()  # Tuple for holding the skills.
        for requested_skill in skills:
            # Look for matches in list of requested skills.
            if person["skills"] is not None:
                # Check to see if person has skills at all.
                if requested_skill in person["skills"]:
                    # A match is found.
                    matching_person = person["employeeId"]
                    skills_tuple += (requested_skill,)  # Record the matched skill.
        if matching_person is not None:
            # At the end of the loop,
            # if a person with a matching skill has been found,
            # append him to the list which is to be returned.
            matching_people.append((matching_person, skills_tuple,))
    if len(matching_people) != 0:
        # Check out the allocations for all found people.
        matching_people = sort_by_time(matching_people, allocations, year_week)
    return matching_people


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
    was_found = False  # A flag for detecting whether an entry with the same week already existed.
    for i in range(len(allocList)):
        # Go through the list to find the appropriate index.
        if allocList[i][0] == tmpAlloc[0]:
            # A match is found where the new allocation and an existing allocation
            # take place on the same week.
            tmp = list(allocList[i])
            tmp[1] += tmpAlloc[1]
            allocList[i] = tuple(tmp)
            if allocList[i][1] == 1.0:
                # If it turns out a week was full because of multiple pre-existing allocations,
                # remove that item.
                del allocList[i]
            was_found = True  # A match was found and handled.
            break  # After the match was handled, there is no further need to loop through the list.
    if not was_found:
        # If the new item did not previously exist on the list, it is now added in.
        insort_left(allocList, tmpAlloc)
    return allocList


def add_person_in_order(people: List, new_person: Tuple) -> List:
    """
    This function is invoked at the end of sort_by_time.
    It is used to add new people with their time allocations into the final
    list which is to be put out.

    :param people: The list to which the new person is to be added.
    :param new_person: The new person to be added into the list.
    :return: The list with the new person added in.
    """
    if not people:
        # List is empty. Add the first item.
        people.append(new_person)
        return people
    was_added = False  # A flag for detecting whether the new person could be added during the loop.
    for i in range(len(people)):
        # Loop through the list and add the new person to the appropriate position.
        # (731, ('C',), (('2020-W47', 0.0),))   # Format of a person on the list.
        if people[i][2][0][0] >= new_person[2][0][0]:
            # If the new person is on the same week, or on an earlier week
            if people[i][2][0][1] >= new_person[2][0][1]:
                # Existing entry is more preoccupied than the new person.
                people.insert(i, new_person)
                was_added = True
                break  # After insertion, there is no need to loop through the list.
        else:
            # NOTE: this block might or might not be necessary.
            people.insert(i, new_person)
            break  # After insertion, there is no need to loop through the list.
    if not was_added:
        # Person could not be added during the loop, so they will be added to the end of the list.
        people.append(new_person)
    return people


def sort_by_time(matching_people: List, allocations_dict: Dict, year_week: str) -> List:
    """
    This function takes the list of all the people with the matching skills,
    looks to see if they have available time slots and adds those in order.

    :param matching_people: A list containing people whose skills matched the request.
    :param allocations_dict: The output of the allocations API represented as a Dict.
    :param year_week: The expected time for candidate to be available. The form is year-Wweek. For example, 2020-W32
    :return: list sorted with most available people at the top.
    """
    tmp_list = []
    for person in matching_people:
        # Cycle through all the people who were matched.
        alloc_list = []
        if person[0] in allocations_dict:
            for allocation in allocations_dict[person[0]]:
                # In the JSON structure of allocations, the base level units are divided
                # into two entities: "user" and "projects"
                if allocation["yearWeek"] >= year_week:
                    # Detect weeks equal or later than param yearWeek
                    if allocation["percentage"] < 100:
                        # Allocation is not completely taken.
                        tmpAlloc = (
                            allocation["yearWeek"],
                            float(allocation["percentage"]) / 100,
                        )
                        alloc_list = add_to_week_allocation(alloc_list, tmpAlloc)
                        if len(alloc_list) == 10:
                            break  # Ten entries is enough.
        else:
            # Subject had no allocations.
            insort_left(alloc_list, (year_week, 0.0,))
        # All allocations extracted for person
        if alloc_list:
            # Only persons for whom allocations were available.
            person = person + (tuple(alloc_list),)
            # Add in the remaining people, who are preoccupied but who are otherwise qualified.
            tmp_list = add_person_in_order(tmp_list, person)
    return tmp_list  # Return the sorted list.


if __name__ == "__main__":
    # For debugging

    print("Breakpoint here")
