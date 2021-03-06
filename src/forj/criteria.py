import re

CRITERIA_SEPARATOR = "-"
RANGE_CRITERIA_SEPARATOR = "/"
FREE_CRITERIA_SEPARATOR = "?"
CHOICE_CRITERIA_SEPARATOR = "|"

criteria_regex = re.compile(
    r"(?P<name>\w+)\((?P<value>[\w\{}\{}\{}]+)\)".format(
        FREE_CRITERIA_SEPARATOR, RANGE_CRITERIA_SEPARATOR, CHOICE_CRITERIA_SEPARATOR
    )
)


class CriteriaSet(object):
    def __init__(self, criterias):
        self.criterias = sorted(
            criterias, key=lambda criteria: criteria.name, reverse=True
        )

    @classmethod
    def from_reference(cls, reference, separator=CRITERIA_SEPARATOR):

        segments = reference.split(separator)

        criterias = filter(lambda value: value is not None, [
            get_criteria_class(segment).from_segment(segment) for segment in segments
        ])

        return cls(criterias)

    def __len__(self):
        return len(self.criterias)

    def is_empty(self):
        return len(self) == 0

    def __iter__(self):
        for criteria in self.criterias:
            yield criteria

    def __repr__(self):
        value = ", ".join(["{}".format(criteria) for criteria in self.criterias])

        return "<{}: {}>".format(self.__class__.__name__, value)

    def __contains__(self, value):
        if len(self.criterias) != len(value.criterias):
            return False

        return all(
            [
                criteria in self.criterias[i]
                for i, criteria in enumerate(value.criterias)
            ]
        )


class Criteria(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    @classmethod
    def from_segment(cls, segment):
        match = criteria_regex.match(segment)

        if not match:
            return None

        return cls(name=match.group("name"), value=match.group("value"))

    def __repr__(self):
        return "<{}: {}:{}>".format(self.__class__.__name__, self.name, self.value)

    def __eq__(self, criteria):
        return criteria.name == self.name and criteria.value == self.value

    def __contains__(self, value):
        return self == value

    def __str__(self):
        return "{}: {}".format(self.name, self.value)


class RangeCriteria(Criteria):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        start, end = self.value.split(RANGE_CRITERIA_SEPARATOR)

        self.value = range(int(start), int(end) + 1)

    def __eq__(self, criteria):
        return criteria.name == self.name and int(criteria.value) in self.value


class ChoiceCriteria(Criteria):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.value = self.value.split(CHOICE_CRITERIA_SEPARATOR)

    def __eq__(self, criteria):
        return criteria.name == self.name and criteria.value in self.value


class FreeCriteria(Criteria):
    def __eq__(self, criteria):
        return criteria.name == self.name


def get_criteria_class(segment):
    if RANGE_CRITERIA_SEPARATOR in segment:
        return RangeCriteria

    if CHOICE_CRITERIA_SEPARATOR in segment:
        return ChoiceCriteria

    if FREE_CRITERIA_SEPARATOR in segment:
        return FreeCriteria

    return Criteria
