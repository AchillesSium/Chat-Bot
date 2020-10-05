from pathlib import Path
from typing import Union, MutableMapping, Any, NewType, MutableSequence

import yaml
import pandas as pd
from tqdm import tqdm
import nltk

# Not sure this will be correct always
from bot.data_api.datasource import Datasource

SkillData = NewType("SkillData", MutableMapping[str, Union[MutableSequence[str], None]])
YAML = NewType("YAML", MutableMapping[str, Any])


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
    sentence = sentence.replace("\u2022", "")

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

        pass

    def recommend_skills_to_user(self, employee_id: int) -> MutableSequence[str]:
        """ Recommend skills to user based on CF

        @param employee_id: ID of employee for whom to recommend skills
        @return: List of skills recommended to user
        """
        ...


if __name__ == "__main__":
    # For debugging
    rec = SkillRecommenderCF()

    print("Breakpoint here")
