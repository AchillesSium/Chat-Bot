import random

from bot.recommenders.skill_recommender import SkillRecommenderCF, SkillRecommendation


sample_skills = [
    "aws",
    "azure",
    "node.js",
    "python",
    "c++",
    "java",
    "testing",
    "ios",
    "android",
    "windows",
    "linux",
    "front end",
    "frontend",
    "back end",
    "backend",
    "full web stack",
    "web",
    "web application design",
    "web applications",
    "web framework",
    "web frameworks",
]


class MockDatasource:
    skills = {
        i: random.sample(sample_skills, random.randint(1, len(sample_skills) - 11))
        for i in range(750, 800)
    }

    def skills_by_user(self):
        return self.skills


recommender = SkillRecommenderCF(MockDatasource())  # type: ignore
user_id = 775


def test_nb_recommendations():
    for nb in [2, 5, 10]:
        rec = recommender.recommend_skills_to_user(user_id, nb_recommendations=nb)
        assert (
            len(rec.recommendation_list) == nb
        ), "Recommender did not return correct number of recommendations"


def test_ignore_skills():
    rec = recommender.recommend_skills_to_user(user_id)

    ignore = random.sample(rec.recommendation_list, 2)
    not_ignored = [s for s in rec.recommendation_list if s not in ignore]

    new_rec = recommender.recommend_skills_to_user(user_id, ignored_skills=ignore)

    assert all(
        ign not in new_rec.recommendation_list for ign in ignore
    ), "Recommender did not correctly ignore skills"
    assert all(
        n_ign in new_rec.recommendation_list for n_ign in not_ignored
    ), "Recommender ignored too many skills"
