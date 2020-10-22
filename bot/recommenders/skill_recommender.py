from dataclasses import dataclass
from pathlib import Path
from collections import Counter, defaultdict, abc
import numpy as np
import re
from typing import (
    Optional,
    MutableMapping,
    Any,
    NewType,
    MutableSequence,
    Set,
    Tuple,
    Dict,
)

import yaml
import pandas as pd
from tqdm import tqdm
import nltk
from sklearn.metrics.pairwise import pairwise_distances, cosine_similarity
from scipy.spatial.distance import cosine as cosine_distance
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


def recursive_update_dict(dict1, dict2):
    """ Recursively merge dictionaries.

    :param dict1: Base dictionary to merge.
    :param dict2: Dictionary to merge on top of base dictionary.
    :return: Merged dictionary
    """
    for key, val in dict1.items():
        if isinstance(val, abc.Mapping):
            dict2_node = dict2.setdefault(key, {})
            recursive_update_dict(val, dict2_node)
        else:
            if key not in dict2:
                dict2[key] = val

    return dict2


def read_yaml(path: Path) -> YAML:
    """ Read yaml into dict from path

    @param path: yaml file path
    @return: yaml dict
    """
    with path.open("r") as f:
        return yaml.safe_load(f)


def clean_one(sentence: str, settings: MutableMapping[str, Any]):
    """ Clean a sentence.
    Includes stripping whitespace, removing non-characters.

    :param sentence: Sentence to clean
    :type sentence: str
    :return: Cleaned sentence
    :rtype: str
    """
    to_remove = [
        "\u2022",
        "\u2019",
        "`",
        "´",
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
        "!",
        "?",
    ]
    for i in to_remove:
        sentence = sentence.replace(i, "")

    if settings["remove_numbers"]:
        sentence = re.sub(r"[0-9]+\b", "", sentence)

    sentence = sentence.strip()

    return sentence


def split_sentence(sentence: str):
    # return nltk.tokenize.word_tokenize(sentence)
    return sentence.split()


def clean_skills(data: SkillData, settings: MutableMapping[str, Any]) -> SkillData:
    """ Clean the skill elements in the data.
    Includes stripping whitespace, removing non-characters.

    :param data: Data to clean
    :return: Cleaned data
    """
    cleaned_data = {}
    for employee_id, skills in data.items():
        if skills is not None:
            tmp = []
            for s in skills:
                cl_s = clean_one(s, settings)

                max_size = settings["skill_features"]["max_word_count"]
                if max_size < 1 or len(nltk.tokenize.word_tokenize(cl_s)) <= max_size:
                    tmp.append(cl_s)

            if len(tmp) > 0:
                cleaned_data[employee_id] = tmp

    return cleaned_data


class SkillExtractor:
    def __init__(self, feat_config: YAML):
        self.config = feat_config

        chunker_patterns = """
        P: {(<VBG>|<JJ>)*(<NN>|<NNP>|<NNS>)+}
        """
        self.chunker = nltk.RegexpParser(chunker_patterns)

    @staticmethod
    def _stem_skills(skills: MutableSequence[str], stemmer: nltk.StemmerI):
        def is_non_stem_word(the_word: str):
            no_stem = [
                "js",
                "aws",
                "kubernetes",
                "windows",
                "sales",
                "jquery",
                "apache",
            ]

            return any(the_word.lower().endswith(ns) for ns in no_stem)

        result = []
        for skill in skills:
            words = split_sentence(skill)
            stemmed_skill = " ".join(
                stemmer.stem(word) if not is_non_stem_word(word) else word
                for word in words
            )
            result.append(stemmed_skill)

        return result

    def extract_skill_features(
        self, data: SkillData
    ) -> Tuple[SkillData, Dict[str, str]]:
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
        stemmer_name = self.config["stemming"]
        stemmers = {
            "porter": nltk.PorterStemmer(),
            "snowball": nltk.SnowballStemmer("english"),
            "lanc": nltk.LancasterStemmer(),
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

        if stemmer_name:
            for key, stemmer in stemmers.items():
                if stemmer_name.lower().startswith(key):
                    break
        else:
            available = ", ".join(stemmers)
            raise AttributeError(
                f"Stemmer {stemmer_name!r} not recognized! Available options are: {available}"
            )

        skill_features = {}
        skill_key = {}
        for employee_id, skills in data.items():
            if skills is not None:
                skill_feat = feat_func(skills)
                no_post_skill = skill_feat

                if self.config["use_lowercase"]:
                    skill_feat = [s.lower() for s in skill_feat]

                if stemmer_name:
                    skill_feat = self._stem_skills(skill_feat, stemmer)

                # Remove empty, if they exist
                to_del = []
                for i, s in enumerate(skill_feat):
                    if s == "":
                        to_del.append(i)

                for i in to_del:
                    del skill_feat[i]
                    del no_post_skill[i]

                skill_features[employee_id] = skill_feat
                skill_key.update(
                    {
                        processed: unprocessed
                        for processed, unprocessed in zip(skill_feat, no_post_skill)
                    }
                )

            else:
                skill_features[employee_id] = None

        return skill_features, skill_key

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
            "e.g.",
            "eg",
            "e.g",
            "i.e.",
            "i.e",
            "ie",
        ] + nltk.corpus.stopwords.words("english")

        result = []
        for s in skills:
            words = split_sentence(s)
            result.extend(w for w in words if w.lower() not in ignored)

        return result

    def _extract_skills(self, skills: MutableSequence[str]):
        return skills

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
            phrases = self._extract_phrases(s)
            result.extend(phrases)

        return result


class SimilarityClac:
    def __init__(self, metric_name: str, nb_workers: int):
        self.metric = metric_name.lower()
        self.nb_workers = nb_workers

        similarity_functions = {
            "cosine": self._cosine_similarity,
            "jaccard similarity": self._jaccard_similarity,
            "dot product": self._dot_similarity,
            "adjusted cosine": self._adjusted_cosine_similarity,
        }

        for m, func in similarity_functions.items():
            if m.startswith(self.metric.split("-")[0]):
                self._similarity_func = func
                break
        else:
            available = ", ".join(similarity_functions)
            raise AttributeError(
                f"Similarity metric {metric_name} not recognized! Available options are: {available}"
            )

    def __call__(self, skill_data):
        return self._similarity_func(skill_data)

    def _cosine_similarity(self, skill_data: pd.DataFrame):
        """Calculate the column-wise cosine similarity for a sparse
            matrix. Return a new dataframe matrix with similarities.
        """
        # data_sparse = sparse.csr_matrix(skill_data)
        # similarities = cosine_similarity(data_sparse.transpose())

        similarities = 1 - pairwise_distances(
            skill_data.T, metric="cosine", n_jobs=self.nb_workers
        )

        sim = pd.DataFrame(
            data=similarities, index=skill_data.columns, columns=skill_data.columns
        )
        return sim

    def _jaccard_similarity(self, skill_data: pd.DataFrame):
        # Jaccard similarity is 1 - hamming distance
        jac_sim = 1 - pairwise_distances(
            skill_data.T, metric="hamming", n_jobs=self.nb_workers
        )

        sim = pd.DataFrame(
            data=jac_sim, index=skill_data.columns, columns=skill_data.columns
        )
        return sim

    def _dot_similarity(self, skill_data: pd.DataFrame):
        def dot_similarity(item1, item2):
            return np.dot(item1, item2)

        dot = pairwise_distances(
            skill_data.T, metric=dot_similarity, n_jobs=self.nb_workers
        )

        sim = pd.DataFrame(
            data=dot, index=skill_data.columns, columns=skill_data.columns
        )
        return sim

    def _adjusted_cosine_similarity(self, skill_data: pd.DataFrame):
        metric_name = self.metric
        alpha = float(metric_name.split("-")[-1])

        def similarity(item1, item2):
            dot = np.dot(item1, item2)
            n1 = np.linalg.norm(item1)
            n2 = np.linalg.norm(item2)
            comb_n = n1 * n2

            cos = 1 - (dot / comb_n)

            return (comb_n ** alpha) * cos

        similarities = pairwise_distances(
            skill_data.T, metric=similarity, n_jobs=self.nb_workers
        )

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

    def _reload_options(self):
        self.config = read_yaml(
            Path(__file__).parent / "config" / "skill_recommender.yaml"
        )

    def update_options(self, opt: MutableMapping[str, Any], reinitialize: bool = True):
        """ Update the options of the recommender.
        Can also reinitialize recommender after updating options.

        @param opt: Updated options/parameters
        @param reinitialize: Whether or not to also reinitialize the recommender after updating options
        """
        self.config = recursive_update_dict(self.config, opt)

        if reinitialize:
            self.initialize_recommender(reload_options=False)

    def get_user_skills(self, user_id: int):
        if user_id in self.skill_index.index:
            user_skills = [
                skill for skill, sc in self.skill_index.loc[user_id].items() if sc > 0
            ]
        else:
            user_skills = []

        return user_skills

    def initialize_recommender(
        self, ds: Optional[Datasource] = None, reload_options: bool = True
    ):
        if ds is not None:
            self.ds = ds

        # print("Initializing recommender")
        if reload_options:
            self._reload_options()

        skill_extractor = SkillExtractor(self.config["skill_features"])
        similarity_evaluator = SimilarityClac(
            self.config["similarity_metric"], self.config["nb_workers"]
        )

        # print("Fetching skill data")
        raw_skills_by_user = clean_skills(self.ds.skills_by_user(), self.config)

        # print("Extracting skill features")
        user_skills, skill_key = skill_extractor.extract_skill_features(
            raw_skills_by_user
        )
        self.skill_key = skill_key

        # print("Constructing skill index")
        self._make_skill_index(user_skills)
        # print("Constructing skill similarity matrix")
        self.skill_similarity = similarity_evaluator(self.skill_index)

        if self.config["neighbourhood"]["use_neighbourhood"]:
            # print("Evaluating skill neighbours")
            self._eval_skill_neighbours()

        # print("Init done!")

    def clear_recommendation_history(self):
        self.recommendation_history.clear()

    def update_recommendation_history(self, user_id: int, skill: str):
        self.recommendation_history[user_id].add(skill)

    def recommend_skills_to_user(
        self, user_id: int, nb_recommendations: int = 10, nb_most_similar: int = 5
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

        if self.config["convert_back"]:
            rec_skills = [self.skill_key[s] for s in rec_skills]

        return SkillRecommendation(rec_skills, rec_similarities, rec_most_similar)


if __name__ == "__main__":

    def print_recs(recommendation: SkillRecommendation, user_id: int):
        rlist = recommendation.recommendation_list
        slist = recommendation.similarities

        print("Recommended skills for user " + str(user_id))
        for r, s in zip(rlist, slist):
            print(f"\t{r}\t{s}")

        print(
            f"Average recommendation similarity: {np.mean(recommendation.similarities):.3f}"
        )

    # For debugging
    rec = SkillRecommenderCF()
    # user_id = 775
    user_id = 759
    sep = "\n" + 100 * "=" + "\n"

    print("Changing rarest_allowed_skill")
    for i in range(1, 11):
        print(f"Setting rarest_allowed_skill={i}")

        rec.update_options({"rarest_allowed_skill": i})
        new_rec = rec.recommend_skills_to_user(user_id)

        print_recs(new_rec, user_id)
    print(sep)

    print("Changing use_binary")
    for i in [True, False]:
        print(f"Setting use_binary={i}")

        rec.update_options({"rarest_allowed_skill": 2, "use_binary": i})  # Default
        new_rec = rec.recommend_skills_to_user(user_id)

        print_recs(new_rec, user_id)
    print(sep)

    print(f"Changing normalize_skill_vectors")
    for i in [True, False]:
        print(f"Setting normalize_skill_vectors={i}")

        rec.update_options(
            {"use_binary": True, "normalize_skill_vectors": i}  # Default
        )
        new_rec = rec.recommend_skills_to_user(user_id)

        print_recs(new_rec, user_id)
    print(sep)

    print(f"Changing feature_type")
    for i in ["skill", "word", "noun"]:
        print(f"Setting feature_type={i}")

        rec.update_options(
            {
                "normalize_skill_vectors": True,  # Default
                "skill_features": {"feature_type": i},
            }
        )
        new_rec = rec.recommend_skills_to_user(user_id)

        print_recs(new_rec, user_id)
    print(sep)

    print(f"Changing use_lowercase")
    for i in [True, False]:
        print(f"Setting use_lowercase={i}")

        rec.update_options(
            {
                "normalize_skill_vectors": True,  # Default
                "skill_features": {"feature_type": "skill", "use_lowercase": i},
            }
        )
        new_rec = rec.recommend_skills_to_user(user_id)

        print_recs(new_rec, user_id)
    print(sep)

    print(f"Changing similarity_metric")
    for metric in ["cosine", "jaccard", "dot", "adjusted cos-0.5"]:
        print(f"Setting similarity_metric={metric}")

        rec.update_options(
            {"similarity_metric": metric, "skill_features": {"use_lowercase": True}}
        )
        new_rec = rec.recommend_skills_to_user(user_id)

        print_recs(new_rec, user_id)
    print(sep)

    print(f"Changing stemming")
    for stemmer in ["porter", "snowball", "lanc"]:
        print(f"Setting stemming={stemmer}")

        rec.update_options(
            {"similarity_metric": "cosine", "skill_features": {"stemming": stemmer}}
        )
        new_rec = rec.recommend_skills_to_user(user_id)

        print_recs(new_rec, user_id)
    print(sep)

    # rec_for_user = rec.recommend_skills_to_user(user_id)
    # print_recs(rec_for_user, user_id)
    #
    # do_not_repeat = rec_for_user.recommendation_list[0]
    # print(f"Adding {do_not_repeat} to history")
    # rec.update_recommendation_history(user_id, do_not_repeat)
    #
    # new_rec = rec.recommend_skills_to_user(user_id)
    # print_recs(new_rec, user_id)
    #
    # print("Resetting recommendation history")
    # rec.clear_recommendation_history()
    #
    # new_rec = rec.recommend_skills_to_user(user_id)
    # print_recs(new_rec, user_id)
    #
    # print("Changing lowercase setting")
    # rec.update_options(
    #     {
    #         "skill_features": {
    #             "use_lowercase": not rec.config["skill_features"]["use_lowercase"]
    #         }
    #     }
    # )
    #
    # new_rec = rec.recommend_skills_to_user(user_id)
    # print_recs(new_rec, user_id)

    print("Breakpoint here")
