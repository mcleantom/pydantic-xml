from typing import Dict, List, Optional, Tuple, Union

import pydantic as pd
import pytest
from helpers import assert_xml_equal

from pydantic_xml import BaseXmlModel, attr, element, errors, wrapped


def test_xml_declaration():
    class TestModel(BaseXmlModel, tag='model'):
        pass

    xml = '''<?xml version="1.0" encoding="utf-8"?>
    <model/>
    '''

    actual_obj = TestModel.from_xml(xml.encode())
    expected_obj = TestModel()

    assert actual_obj == expected_obj

    actual_xml = actual_obj.to_xml(xml_declaration=True, encoding='utf-8')
    assert_xml_equal(actual_xml, xml.encode())


def test_root_not_found_error():
    class TestModel(BaseXmlModel, tag='model'):
        pass

    xml = '''
    <model1/>
    '''

    with pytest.raises(errors.ParsingError) as err:
        TestModel.from_xml(xml)

    assert len(err.value.args) == 1
    assert err.value.args[0] == 'root element not found (actual: model1, expected: model)'


def test_skip_empty():
    class TestSubModel(BaseXmlModel, tag='model'):
        text: Optional[str] = None
        element1: Optional[str] = element(default=None)
        attr1: Optional[str] = attr(default=None)

    class TestModel(BaseXmlModel, tag='model'):
        model: TestSubModel
        list: List[TestSubModel] = []
        tuple: Optional[Tuple[TestSubModel, TestSubModel]] = None
        attrs: Dict[str, str] = {}
        wrapped: Optional[str] = wrapped('envelope', default=None)

    xml = '''
    <model/>
    '''

    obj = TestModel(model=TestSubModel())

    actual_xml = obj.to_xml(skip_empty=True)
    assert_xml_equal(actual_xml, xml.encode())


def test_model_level_skip_empty_enable():
    class TestSubModel(BaseXmlModel, tag='submodel', skip_empty=True):
        text: Optional[str]
        attr1: Optional[str] = attr()
        element1: Optional[str] = element()

    class TestModel(BaseXmlModel, tag='model'):
        submodel: TestSubModel
        element1: Optional[str] = element()

    xml = '''
    <model>
        <submodel></submodel>
        <element1></element1>
    </model>
    '''

    obj = TestModel(
        submodel=TestSubModel(
            text=None,
            attr1=None,
            element1=None,
        ),
        element1=None,
    )

    actual_xml = obj.to_xml(skip_empty=False)
    assert_xml_equal(actual_xml, xml.encode())


def test_model_level_skip_empty_disable():
    class TestSubModel(BaseXmlModel, tag='submodel', skip_empty=False):
        text: Optional[str]
        attr1: Optional[str] = attr()
        element1: Optional[str] = element()

    class TestModel(BaseXmlModel, tag='model'):
        submodel: TestSubModel
        element1: Optional[str] = element()

    xml = '''
    <model>
        <submodel attr1=""><element1></element1></submodel>
    </model>
    '''

    obj = TestModel(
        submodel=TestSubModel(
            text=None,
            attr1=None,
            element1=None,
        ),
        element1=None,
    )

    actual_xml = obj.to_xml(skip_empty=True)
    assert_xml_equal(actual_xml, xml.encode())


def test_defaults():
    class TestModel(BaseXmlModel, tag='model'):
        attr1: int = attr(default=1)
        element1: int = element(default=1)
        text: str = 'text'
        attrs: Dict[str, str] = element(tag='model2', default={'key': 'value'})
        element2: int = wrapped('wrapper', element(tag='model3', default=2))

    xml = '<model/>'
    actual_obj: TestModel = TestModel.from_xml(xml)
    expected_obj: TestModel = TestModel()
    assert actual_obj == expected_obj

    expected_xml = '''
        <model attr1="1">text<element1>1</element1><model2 key="value"/><wrapper><model3>2</model3></wrapper></model>
    '''
    actual_xml = actual_obj.to_xml(skip_empty=True)
    assert_xml_equal(actual_xml, expected_xml.encode())


def test_default_factory():
    class TestModel(BaseXmlModel, tag='model'):
        attr1: int = attr(default_factory=lambda: 1)
        element1: int = element(default_factory=lambda: 1)
        text: str = 'text'
        attrs: Dict[str, str] = element(tag='model2', default_factory=lambda: {'key': 'value'})
        element2: int = wrapped('wrapper', element(tag='model3', default_factory=lambda: 2))

    xml = '<model/>'
    actual_obj: TestModel = TestModel.from_xml(xml)
    expected_obj: TestModel = TestModel()
    assert actual_obj == expected_obj

    expected_xml = '''
        <model attr1="1">text<element1>1</element1><model2 key="value"/><wrapper><model3>2</model3></wrapper></model>
    '''
    actual_xml = actual_obj.to_xml(skip_empty=True)
    assert_xml_equal(actual_xml, expected_xml.encode())


def test_field_serialization_exclude():
    class TestModel(BaseXmlModel, tag='model'):
        element1: int = element(exclude=True)
        element2: int = element(exclude=False)

    xml = '''
        <model>
            <element1>1</element1>
            <element2>2</element2>
        </model>
    '''

    actual_obj: TestModel = TestModel.from_xml(xml)
    expected_obj = TestModel(element1=1, element2=2)
    assert actual_obj == expected_obj

    expected_xml = '''
        <model>
            <element2>2</element2>
        </model>
    '''
    actual_xml = actual_obj.to_xml()
    assert_xml_equal(actual_xml, expected_xml.encode())


def test_model_params_inheritance():
    class BaseModel(
        BaseXmlModel,
        tag='TestTag',
        ns='TestNamespace',
        nsmap={'test': 'value'},
        ns_attrs=True,
        search_mode='ordered',
    ):
        pass

    class TestModel(BaseModel):
        pass

    assert TestModel.__xml_tag__ == BaseModel.__xml_tag__
    assert TestModel.__xml_ns__ == BaseModel.__xml_ns__
    assert TestModel.__xml_nsmap__ == BaseModel.__xml_nsmap__
    assert TestModel.__xml_ns_attrs__ == BaseModel.__xml_ns_attrs__
    assert TestModel.__xml_search_mode__ == BaseModel.__xml_search_mode__


def test_pydantic_validation_context():
    validation_context = {'var1': 1, 'var2': True}

    class TestSubModel(BaseXmlModel, tag='submodel'):
        attr1: int = attr()

        @pd.field_validator('attr1')
        @classmethod
        def validate_field(cls, v: str, info: pd.FieldValidationInfo):
            assert info.context == validation_context
            return v

    class TestModel(BaseXmlModel, tag='model'):
        submodel: TestSubModel
        submodel_union: Union[TestSubModel, TestSubModel]
        submodel_wrapped: TestSubModel = wrapped('wrapper')
        submodel_tuple: Tuple[TestSubModel, TestSubModel]
        submodel_list: List[TestSubModel]

        @pd.field_validator('submodel')
        @classmethod
        def validate_field(cls, v: str, info: pd.FieldValidationInfo):
            assert info.context == validation_context
            return v

    xml = '''
        <model>
            <submodel attr1="0"/>
            <submodel attr1="1"/>
            <wrapper>
                <submodel attr1="2"/>
            </wrapper>
            <submodel attr1="3"/>
            <submodel attr1="4"/>
            <submodel attr1="5"/>
            <submodel attr1="6"/>
            <submodel attr1="7"/>
        </model>
    '''

    TestModel.from_xml(xml, validation_context)
