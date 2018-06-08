from typing import Dict, List
import numbers
from etk.knowledge_graph_schema import KGSchema
from etk.field_types import FieldType
from etk.etk_exceptions import KgValueError, UndefinedFieldError
from etk.knowledge_graph_provenance_record import KnowledgeGraphProvenanceRecord
from etk.extraction import Extraction
from etk.segment import Segment
from etk.utilities import Utility


class KnowledgeGraph(object):
    """
    This class is a knowledge graph object, provides API for user to construct their kg.
    Add field and value to the kg object, analysis on provenance
    """

    def __init__(self, schema: KGSchema, doc) -> None:
        self._kg = {}
        self.origin_doc = doc
        self.schema = schema

    def validate_field(self, field_name: str) -> bool:
        """
        Complain if a field in not in the schema
        Args:
            field_name:

        Returns: True if the field is present.

        """
        result = self.schema.has_field(field_name)
        if not result:
            # todo: how to comply with our error handling policies?
            raise UndefinedFieldError("'{}' should be present in the knowledge graph schema.".format(field_name))
        return result

    def _add_single_value(self, field_name: str, value, provenance_path=None,
                          reference_type="location") -> bool:
        (valid, this_value) = self.schema.is_valid(field_name, value)
        if valid:
            if {
                "value": this_value,
                "key": self.create_key_from_value(this_value, field_name)
            } not in self._kg[field_name]:
                self._kg[field_name].append({
                    "value": this_value,
                    "key": self.create_key_from_value(this_value, field_name)
                })
            self.create_kg_provenance(reference_type, str(this_value), provenance_path) \
                if provenance_path else self.create_kg_provenance(reference_type, str(this_value))
            return True
        else:
            return False

    def _add_value(self, field_name: str, value, provenance_path=None) -> bool:
        """
        Helper function to add values to a knowledge graph
        Args:
            field_name: a field in the knowledge graph, assumed correct
            value: any Python type

        Returns: True if the value is compliant with the field schema, False otherwise

        """
        if not isinstance(value, list):
            value = [value]

        all_valid = True
        for x in value:
            valid = self._add_single_value(field_name, x, provenance_path=provenance_path)
            all_valid = all_valid and valid
        return all_valid

    def _add_doc_value(self, field_name: str, jsonpath: str) -> None:
        """
        Add a value to knowledge graph by giving a jsonpath

        Args:
            field_name: str
            jsonpath: str

        Returns:
        """
        path = self.origin_doc.etk.parse_json_path(jsonpath)
        matches = path.find(self.origin_doc.value)
        all_valid = True
        for a_match in matches:
            # If the value is the empty string, we treat is a None.
            if a_match.value:
                valid = self._add_value(field_name, a_match.value, provenance_path=str(a_match.full_path))
                all_valid = all_valid and valid

        if not all_valid:
            raise KgValueError("Some kg value type invalid according to schema")

    def add_value(self, field_name: str, value: object = None, json_path: str = None,
                  json_path_extraction: str = None) -> None:
        """
        Add a value to knowledge graph.
        Input can either be a value or a json_path. If the input is json_path, the helper function _add_doc_value is
        called.
        If the input is a value, then it is handled

        Args:
            field_name: str, the field name in the knowledge graph
            value: the value to be added to the knowledge graph
            json_path: str, if json_path is provided, then get the value at this path in the doc
            json_path_extraction: str,

        Returns:
        """
        self.validate_field(field_name)
        if field_name not in self._kg:
            self._kg[field_name] = []

        if json_path:
            self._add_doc_value(field_name, json_path)

        if value:
            if not isinstance(value, list):
                value = [value]

            all_valid = True
            for a_value in value:
                if isinstance(a_value, Extraction):
                    valid = self._add_single_value(field_name, a_value.value, provenance_path=str(json_path_extraction))
                elif isinstance(a_value, Segment):
                    valid = self._add_single_value(field_name, a_value.value, provenance_path=a_value.json_path)
                else:
                    valid = self._add_single_value(field_name, a_value, provenance_path=json_path_extraction,
                                                   reference_type="constant")

                all_valid = all_valid and valid

            if not all_valid:
                print("Some kg value type invalid according to schema")
                # raise KgValueError("Some kg value type invalid according to schema")

    @property
    def value(self) -> Dict:
        """
        Get knowledge graph object

        Args:

        Returns: Dict
        """
        return self._kg

    def get_values(self, field_name: str) -> List[object]:
        """
        Get a list of all the values of a field.

        Args:
            field_name:

        Returns: the list of values (not the keys)

        """
        result = list()
        if self.validate_field(field_name):
            for value_key in self._kg.get(field_name):
                result.append(value_key["value"])
        return result

    def create_key_from_value(self, value, field_name: str):
        """

        Args:
            value:
            field_name: str
        Returns: key

        """
        key = value
        if self.schema.field_type(field_name) == FieldType.KG_ID:
            pass
        elif (isinstance(key, str) or isinstance(key, numbers.Number)) and self.schema.field_type(
                field_name) != FieldType.DATE:
            # try except block because unicode characters will not be lowered
            try:
                key = str(key).strip().lower()
            except:
                pass

        return key

    def create_kg_provenance(self, reference_type, value, json_path: str = None) -> None:
        new_id = self.origin_doc.provenance_id_index
        kg_provenance_record: KnowledgeGraphProvenanceRecord = KnowledgeGraphProvenanceRecord(new_id,
                                                                                              "kg_provenance_record",
                                                                                              reference_type, value,
                                                                                              json_path,
                                                                                              self.origin_doc)
        self.origin_doc.provenance_id_index_incrementer()
        if value in self.origin_doc.kg_provenances:
            self.origin_doc.kg_provenances[value].append(new_id)
        else:
            self.origin_doc.kg_provenances[value] = [new_id]
        self.origin_doc.provenances[new_id] = kg_provenance_record
        if "provenances" not in self.origin_doc.cdr_document:
            self.origin_doc.cdr_document["provenances"] = []
        _dict = self.get_dict_kg_provenance(kg_provenance_record)
        self.origin_doc.cdr_document["provenances"].append(_dict)

    @staticmethod
    def get_dict_kg_provenance(kg_provenance_record: KnowledgeGraphProvenanceRecord):
        _dict = dict()
        _dict["@id"] = kg_provenance_record.id
        _dict["@type"] = kg_provenance_record._type
        _dict["reference_type"] = kg_provenance_record.reference_type
        _dict["value"] = kg_provenance_record._value
        if kg_provenance_record.json_path is not None:
            _dict["json_path"] = kg_provenance_record.json_path
        return _dict