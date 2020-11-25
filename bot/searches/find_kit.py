from typing import List, Dict, Tuple, Iterable
from collections import Counter
from datetime import timedelta
from itertools import islice

from bot.helpers import YearWeek


def find_person_by_skills(
    skills: List[str], users: Dict, allocations: Dict, year_week: str
):
    """Look for people with a certain set of skills.

    This function assembles a list of people with matching skills, who are available.
    Finally, it sorts the the assembled list by their matching skills and available hours.

    :param skills: A list containing names of requested skills.
    :param users: User information output of the Data API.
    :param allocations: Allocation information output of the Data API.
    :param year_week: The week for which available workers are being searched for.
    :return: A List containing found persons, sorted by the number of matching skills and their availability in time.
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
            # collect the allocations for the person

            # all allocations within year from year_week
            start_week = YearWeek.from_string(year_week)
            all_alloc = chronological_allocations(
                allocations.get(matching_person, ()),
                start_week,
                start_week + timedelta(weeks=52),
            )

            # allocations under 100%
            non_full_alloc = (
                (week, percentage / 100)
                for week, percentage in all_alloc
                if percentage < 100
            )

            # take at most 10 first allocations
            alloc = list(islice(non_full_alloc, 10))

            # if person has any week with under 100% allocation
            # append him to the list which is to be returned.
            if alloc:
                matching_people.append((matching_person, skills_tuple, alloc))
    # Sort people by
    #  1. greatest number of matching skills
    #  2. earliest available time
    #  3. smallest allocation percent
    matching_people = sorted(
        matching_people,
        key=lambda person: (-len(person[1]), person[2][0][0], person[2][0][1]),
    )
    return matching_people


def chronological_allocations(
    allocations: Iterable[dict], start_week: YearWeek, end_week: YearWeek
) -> Iterable[Tuple[str, int]]:
    """ Generator of weekly allocations in chronological order

    Yields allocations between start_week and end_week inclusive.
    Allocation is two element tuple:
    - the year_week as string
    - the allocation percentage in range [0,100]

    :param allocations: The allocations to consider
    :param start_week: The week to start from
    :param end_week: The last week to include
    :return: generator of allocations in chronological order
    """
    if start_week > end_week:
        return
    alloc = Counter()
    for allocation in allocations:
        alloc[allocation["yearWeek"]] += allocation["percentage"]
    for yw in start_week.iter_weeks():
        if yw > end_week:
            return
        yield (str(yw), alloc[str(yw)])
