`config/`: Config files for recommendations
`skill_recommender.py`: Module for skill recommendation using collaborative filtering
- `SkillRecommenderCF`: Collaborative filtering recommender for skills
    - `initialize_recommender()`: (Re)initialize recommender. Reads and fits data again.
    - `recommend_skills_to_user(user_id: int, skill: str)`: Adds `skill` to recommendation history of `user_id` so that it won't be recemmended again.
    - `clear_recommendation_history()`: Clears recommendation history
    - `recommend_skills_to_user(user_id: int, nb_recommendations: int, nb_most_similar: int)`: Gets `nb_recommendations` recommended skills for `user_id` and `nb_most_similar` most similar skills of the user. Returns a `SkillRecommendation`.
- `SkillRecommendation`: Return type of recommender
    - `recommendation_list: list[str]`: List of recommended skills
    - `similarities: list[float]`: List of similarities for the recommended skills
    - `most_similar_to: list[str]`: List of the user's skills that the recommended skills are most similar to
