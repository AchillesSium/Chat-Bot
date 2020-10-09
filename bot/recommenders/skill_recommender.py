from dataclasses import dataclass
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from typing import Optional, MutableMapping, Any, NewType, MutableSequence, Set

import yaml
import pandas as pd
from tqdm import tqdm
import nltk
from sklearn.metrics.pairwise import cosine_similarity
from scipy import sparse

# Not sure this will be correct always
from bot.data_api.datasource import Datasource

SkillData = NewType("SkillData", MutableMapping[str, Optional[MutableSequence[str]]])
YAML = NewType("YAML", MutableMapping[str, Any])


@dataclass
class SkillRecommendation:
    recommendation_list: MutableSequence[str]
    similarities: MutableSequence[float]
    most_similar_to: MutableSequence[str]


def read_yaml(path: Path) -> YAML:
    """ Read yaml into dict from path

    @param path: yaml file path
    @return: yaml dict
    """
    with path.open("r") as f:
        return yaml.safe_load(f)


def clean_one(sentence: str):
    """ Clean a sentence.
    Includes stripping whitespace, removing non-characters.

    :param sentence: Sentence to clean
    :type sentence: str
    :return: Cleaned sentence
    :rtype: str
    """
    to_remove = [
        "\u2022",
        "●",
        '"',
        "'",
        "“",
        "”",
        "♡",
        "-",
        "_",
        ".",
        ",",
        ":",
        ";",
        "⁃",
    ]

    for i in to_remove:
        sentence = sentence.replace(i, "")

    return sentence.strip()


def clean_skills(data: SkillData) -> SkillData:
    """ Clean the skill elements in the data.
    Includes stripping whitespace, removing non-characters.

    :param data: Data to clean
    :return: Cleaned data
    """
    cleaned_data = {}
    for employee_id, skills in data.items():
        if skills is not None:
            cleaned_data[employee_id] = [clean_one(s) for s in skills]

    return cleaned_data


class SkillExtractor:
    def __init__(self, feat_config: YAML):
        self.config = feat_config

        chunker_patterns = """
        P: {(<VBG>|<JJ>)*(<NN>|<NNP>|<NNS>)+}
        """
        self.chunker = nltk.RegexpParser(chunker_patterns)

    def extract_skill_features(self, data: SkillData) -> SkillData:
        """ Create new SkillData dict with extracted features

        @param data: Raw
        @return:
        """
        skill_feat_type = self.config["feature_type"]
        feat_functions = {
            "noun": self._extract_noun_phrases,
            "skill": self._extract_skills,
            "word": self._extract_words,
        }
        # Python dictionaries guarantee insertion ordering starting from 3.7
        for key, feat_func in feat_functions.items():
            if skill_feat_type.lower().startswith(key):
                break
        else:
            available = ", ".join(feat_functions)
            raise AttributeError(
                f"Skill feature {skill_feat_type!r} not recognized! Available options are: {available}"
            )

        skill_features = {}
        for employee_id, skills in data.items():
            if skills is not None:
                skill_features[employee_id] = feat_func(skills)
            else:
                skill_features[employee_id] = None

        return skill_features

    def _extract_words(self, skills: MutableSequence[str]):
        ignored = [
            "a",
            "an",
            "the",
            "i",
            "of",
            "at",
            "in",
            "we",
            "implementation",
            "development",
            "for",
            "with",
        ]

        result = []
        for s in skills:
            if self.config["use_lowercase"]:
                words = s.lower().split()
            else:
                words = s.split()
            result.extend(w for w in words if w.lower() not in ignored)

        return result

    def _extract_skills(self, skills: MutableSequence[str]):
        result = []
        for s in skills:
            if self.config["use_lowercase"]:
                result.append(s.lower())
            else:
                result.append(s)

        return result

    def _parse_nounphrases(self, sentence):
        tokens = nltk.word_tokenize(sentence)
        tagged = nltk.pos_tag(tokens)
        return self.chunker.parse(tagged)

    @staticmethod
    def _join_parse_tree(the_tree):
        return " ".join(i[0] for i in the_tree)

    def _extract_phrases(self, skill: str):
        phrases = []
        if len(skill.split()) != 1:
            parsed = self._parse_nounphrases(skill)
            for el in parsed:
                if type(el) == nltk.tree.Tree:
                    if el.label() == "P":
                        phrases.append(self._join_parse_tree(el))

        else:
            phrases.append(skill)

        return phrases

    def _extract_noun_phrases(self, skills: MutableSequence[str]):
        result = []
        for s in skills:
            if self.config["use_lowercase"]:
                phrases = self._extract_phrases(s.lower())
            else:
                phrases = self._extract_phrases(s)
            result.extend(phrases)

        return result


class SimilarityClac:
    def __init__(self, metric_name: str):
        self.metric = metric_name.lower()

        if self.metric.startswith("cosine"):
            self._similarity_func = self._cosine_similarity
        else:
            raise AttributeError(
                f"Unknown similarity metric {metric_name}!\nCurrently implemented:\n\tcosine similarity\n."
            )

    def __call__(self, skill_data):
        return self._similarity_func(skill_data)

    @staticmethod
    def _cosine_similarity(skill_data):
        """Calculate the column-wise cosine similarity for a sparse
            matrix. Return a new dataframe matrix with similarities.
        """
        data_sparse = sparse.csr_matrix(skill_data)
        similarities = cosine_similarity(data_sparse.transpose())

        sim = pd.DataFrame(
            data=similarities, index=skill_data.columns, columns=skill_data.columns
        )
        return sim


class SkillRecommenderCF:
    def __init__(self, ds: Optional[Datasource] = None):
        if ds is not None:
            self.ds = ds
        else:
            self.ds = Datasource()

        self.initialize_recommender()

        # Keep track of recommendations so as to not recommend the same thing multiple times
        self.recommendation_history = defaultdict(set)

    def _normalize_skill_vectors(self):
        """ Normalize user skill vectors in skill index to unit vectors
        This makes individual skills count less.
        """
        magnitude = np.sqrt(np.square(self.skill_index).sum(axis=1))

        self.skill_index = self.skill_index.divide(magnitude, axis="index")

    def _get_rarity_filtered_skills(self, user_skills: SkillData) -> Set[str]:
        """ Get all skills from skills by user.
        If needed (determined by self.config), removes rare skills.

        @param user_skills: Skill list for each user
        @return: Set of all (filtered) skills
        """
        all_skills = set()
        for _, skills in user_skills.items():
            if skills:
                all_skills.update(skills)

        # Ignore rare skills
        rarest_allowed = self.config["rarest_allowed_skill"]
        if rarest_allowed > 1:
            skills_counter = Counter()
            for _, skills in user_skills.items():
                if skills:
                    # constructing the set is necessary, unless the skills can
                    # be guaranteed to be unique
                    skills_counter.update(set(skills))

            for skill, count in skills_counter.items():
                if count < rarest_allowed:
                    all_skills.remove(skill)

        return all_skills

    def _make_skill_index(self, user_skills: SkillData):
        """ Converts skills by user into pd.DataFrame
        Also, if needed, removes rare skills and normalizes skill vectors.
        (Determined by config)

        @param user_skills: Skill list for each user
        """
        all_skills = self._get_rarity_filtered_skills(user_skills)

        sorted_skills = sorted(all_skills)
        sorted_users = sorted(user_skills)

        skill_counters = {}
        for user, skills in user_skills.items():
            cnt = Counter()
            if skills is not None:
                cnt.update(s for s in skills if s in all_skills)
            skill_counters[user] = cnt

        data_dict = {}
        for skill in sorted_skills:
            skill_prevalence = [skill_counters[user][skill] for user in sorted_users]

            if self.config["use_binary"]:
                # Convert e.g. [0, 0, 4, 8, 0] to [0, 0, 1, 1, 0]
                skill_prevalence = list(np.where(np.array(skill_prevalence) > 0, 1, 0))

            data_dict[skill] = skill_prevalence

        self.skill_index = pd.DataFrame(data_dict, index=sorted_users)

        if self.config["normalize_skill_vectors"]:
            self._normalize_skill_vectors()

    def _eval_skill_neighbours(self):
        neigh_size = self.config["neighbourhood"]["neighbourhood_size"]

        data_neighbours = pd.DataFrame(
            index=self.skill_similarity.columns, columns=range(1, neigh_size + 1)
        )
        for i in tqdm(range(0, len(self.skill_similarity.columns))):
            data_neighbours.iloc[i, :neigh_size] = (
                self.skill_similarity.iloc[:, i]
                .sort_values(ascending=False)[:neigh_size]
                .index
            )

        self.skill_neighbours = data_neighbours

    def _get_most_similar(self, recommended_skills, user_skills, sz: int):
        """ Get the list of "most similar" skills in user_skills in relation to recommended_skills

        @param recommended_skills: Recommended skills
        @param user_skills: User skills
        @param sz: How many "most similar" skills to list
        @return: List of "most similar" skills
        """
        similarities: pd.DataFrame = sum(
            self.skill_similarity.loc[rec_skill].loc[user_skills]
            for rec_skill in recommended_skills
        )

        return list(similarities.nlargest(sz).index)

    def get_user_skills(self, user_id: int):
        if user_id in self.skill_index.index:
            user_skills = [
                skill for skill, sc in self.skill_index.loc[user_id].items() if sc > 0
            ]
        else:
            user_skills = []

        return user_skills

    def initialize_recommender(self, ds: Optional[Datasource] = None):
        if ds is not None:
            self.ds = ds

        print("Initializing recommender")
        self.config = read_yaml(
            Path(__file__).parent / "config" / "skill_recommender.yaml"
        )

        skill_extractor = SkillExtractor(self.config["skill_features"])
        similarity_evaluator = SimilarityClac(self.config["similarity_metric"])

        print("Fetching skill data")
        raw_skills_by_user = clean_skills(self.ds.skills_by_user())

        print("Extracting skill features")
        user_skills = skill_extractor.extract_skill_features(raw_skills_by_user)

        print("Constructing skill index")
        self._make_skill_index(user_skills)
        print("Constructing skill similarity matrix")
        self.skill_similarity = similarity_evaluator(self.skill_index)

        if self.config["neighbourhood"]["use_neighbourhood"]:
            print("Evaluating skill neighbours")
            self._eval_skill_neighbours()

        print("Init done!")

    def clear_recommendation_history(self):
        self.recommendation_history.clear()

    def update_recommendation_history(self, user_id: int, skill: str):
        self.recommendation_history[user_id].add(skill)

    def recommend_skills_to_user(
        self, user_id: int, nb_recommendations: int = 5, nb_most_similar: int = 5
    ) -> SkillRecommendation:
        """ Recommend skills to user based on CF

        @param user_id: ID of employee for whom to recommend skills
        @param nb_recommendations: How many recommendations to make
        @param nb_most_similar: How many "most similar" skills of the user to list
        @return: List of skills recommended to user, their similarities and what they are most similar to
        """
        user_skills = self.get_user_skills(user_id)

        if len(user_skills) == 0:
            raise KeyError(f"No skill data found for user {user_id}")

        user_skill_vector = self.skill_index.loc[user_id]

        if not self.config["neighbourhood"]["use_neighbourhood"]:
            score = self.skill_similarity.dot(user_skill_vector).div(
                self.skill_similarity.sum(axis=1)
            )
        else:
            # Construct the neighbourhood from the most similar skills to the
            # ones the user already has.
            most_similar_to_likes = self.skill_neighbours.loc[user_skills]
            similar_list = most_similar_to_likes.values.tolist()
            similar_list = list(
                set(item for sublist in similar_list for item in sublist)
            )
            neighbourhood = self.skill_similarity[similar_list].loc[similar_list]

            # A user vector containing only the neighbourhood items and
            # the known user likes.
            user_vector = self.skill_index.loc[user_id].loc[similar_list]

            score = neighbourhood.dot(user_vector).div(neighbourhood.sum(axis=1))

        # Drop already-known skills
        score = score.drop(user_skills)
        # Drop already-recommended skills
        score = score.drop(self.recommendation_history[user_id])

        # Get top recommendations
        recommendations = score.nlargest(nb_recommendations)

        # Get recommended skills, similarities and most similar
        rec_skills = list(recommendations.index)
        rec_similarities = list(recommendations)
        rec_most_similar = self._get_most_similar(
            rec_skills, user_skills, nb_most_similar
        )

        return SkillRecommendation(rec_skills, rec_similarities, rec_most_similar)


if __name__ == "__main__":

    def print_recs(recommendation: SkillRecommendation, user_id: int):
        rlist = recommendation.recommendation_list

        print("Recommended skills for user " + str(user_id))
        for r in rlist:
            print(f"\t{r}")

    # For debugging
    rec = SkillRecommenderCF()
    user_id = 775

    rec_for_user = rec.recommend_skills_to_user(user_id)
    print_recs(rec_for_user, user_id)

    do_not_repeat = rec_for_user.recommendation_list[0]
    print(f"Adding {do_not_repeat} to history")
    rec.update_recommendation_history(user_id, do_not_repeat)

    new_rec = rec.recommend_skills_to_user(user_id)
    print_recs(new_rec, user_id)

    print("Resetting recommendation history")
    rec.clear_recommendation_history()

    new_rec = rec.recommend_skills_to_user(user_id)
    print_recs(new_rec, user_id)

    print(new_rec)

    print("Breakpoint here")

# TODO: Add option to change recommender settings from slack?
