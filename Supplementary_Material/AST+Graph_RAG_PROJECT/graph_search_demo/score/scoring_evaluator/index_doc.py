from .index import ScoringEvaluator

class ScoringEvaluatorDoc(ScoringEvaluator):

    def get_file_name(self, entity_name):
        unique_elements = []
        parts = entity_name.split(".")
        len_parts = len(parts)
        # print(f'parts :{parts}')

        return parts[0] if len_parts > 0 else ''

    def primary_contains_name(self, primary_file, entity_name):
        file_name  = self.get_file_name(entity_name)
        if file_name == '':
            return False
        return primary_file == file_name

    def nofind_condition(self, score, type):
        return score == 0