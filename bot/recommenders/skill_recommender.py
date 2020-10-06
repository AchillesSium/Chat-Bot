from pathlib import Path
from collections import Counter, namedtuple
import numpy as np
from typing import Union, MutableMapping, Any, NewType, MutableSequence, Set

import yaml
import pandas as pd
from tqdm import tqdm
import nltk

# Not sure this will be correct always
from bot.data_api.datasource import Datasource

SkillData = NewType("SkillData", MutableMapping[str, Union[MutableSequence[str], None]])
YAML = NewType("YAML", MutableMapping[str, Any])

SkillRecommendation = namedtuple(
    "SkillRecommendation", ("recommendation_list", "similarities", "most_similar_to")
)


def read_yaml(path: Path) -> YAML:
    """ Read yaml into dict from path

    @param path: yaml file path
    @return: yaml dict
    """
    return yaml.safe_load(path.open("r"))


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
        "+",
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
        if skill_feat_type.lower().startswith("noun"):
            feat_func = self._extract_noun_phrases
        elif skill_feat_type.lower().startswith("skill"):
            feat_func = self._extract_skills
        elif skill_feat_type.lower().startswith("word"):
            feat_func = self._extract_words
        else:
            raise AttributeError(f"Skill feature {skill_feat_type} not recognized!")

        skill_features = {}
        for employee_id, skills in data.items():
            if skills is not None:
                skill_features[employee_id] = feat_func(skills)
            else:
                skill_features[employee_id] = None

        return skill_features

    def _extract_words(self, skills: MutableSequence[str]):
        result = []
        for s in skills:
            if self.config["use_lowercase"]:
                words = s.lower().split()
            else:
                words = s.split()
            result.extend(words)

        to_del = []
        for i, s in enumerate(result):
            if s.lower() in [
                "a",
                "an",
                "the",
                "i",
                "of",
                "at",
                "in",
                "we",
                "implemetation",
                "development",
                "for",
                "with",
            ]:
                to_del.append(i)

        to_del.reverse()
        for i in to_del:
            del result[i]

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
        return " ".join([i[0] for i in the_tree])

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


class SkillRecommenderCF:
    def __init__(self, ds: Union[Datasource, None] = None):
        if ds is None:
            ds = Datasource()

        self.config = read_yaml(Path("./config/skill_recommender.yaml"))

        self.source = ds
        self.skill_extractor = SkillExtractor(self.config["skill_features"])

        raw_skills_by_user = clean_skills(self.source.skills_by_user())

        user_skills = self.skill_extractor.extract_skill_features(raw_skills_by_user)

        self._make_skill_index(user_skills)

        pass

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
            all_skills.update(set(skills))

        # Ignore rare skills
        rarest_allowed = self.config["rarest_allowed_skill"]
        if rarest_allowed > 1:
            skills_counter = Counter()
            for _, skills in user_skills.items():
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

        sorted_skills = sorted(list(all_skills))
        sorted_users = sorted(list(user_skills.keys()))

        skill_counters = {}
        for user, skills in user_skills.items():
            cnt = Counter()
            cnt.update([s for s in skills if s in all_skills])
            skill_counters[user] = cnt

        data_dict = {}
        for skill in sorted_skills:
            skill_prevalence = [skill_counters[user][skill] for user in sorted_users]
            data_dict[skill] = skill_prevalence

        self.skill_index = pd.DataFrame(data_dict, index=sorted_users)

        if self.config["normalize_skill_vectors"]:
            self._normalize_skill_vectors()

    def recommend_skills_to_user(self, user_id: int) -> SkillRecommendation:
        """ Recommend skills to user based on CF

        @param user_id: ID of employee for whom to recommend skills
        @return: List of skills recommended to user, their similarities and what they are most similar to
        """
        return None


if __name__ == "__main__":
    # For debugging
    rec = SkillRecommenderCF()

    rec_for_775 = rec.recommend_skills_to_user(775)
    print(rec_for_775)

    print("Breakpoint here")
